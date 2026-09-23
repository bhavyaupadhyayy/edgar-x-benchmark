"""Bankruptcy events assembled from one or more 8-K filings.

An original 8-K and its amendments describe ONE bankruptcy but carry different
accession numbers, so accession-level deduplication counts them twice. They
also carry different information: an 8-K/A often supplies the docket number or
petition date the original omitted. Choosing one filing and discarding the rest
throws that away.

So the unit assembled here is an event record that merges its sources rather
than a filing that represents the event. Fields are filled from whichever
source first supplies them, and every contributing accession is retained.

Clustering rules, applied within a single CIK:

  - same docket number                                          same event
  - same chapter and petition dates within MERGE_DAY_TOLERANCE  same event
  - different chapters (7 vs 11) ONLY with strong same-case
    evidence: the EXACT same petition date plus either a stated
    conversion or the same bankruptcy court                    same event
  - an 8-K/A arriving within AMENDMENT_WINDOW_DAYS of an event
    that is still incompletely identified, with a compatible
    disposition and no court conflict                          same event
  - otherwise                                                   a new event

Cross-chapter records are never merged on date tolerance alone: two filers'
Chapter 11 and Chapter 7 cases a day apart are different bankruptcies.

The third rule is restricted to actual /A filings. Applying a 120-day proximity
heuristic to ordinary 8-Ks would merge two genuine bankruptcies of the same
filer, which is a worse error than splitting one.

Anything that cannot be resolved is reported, not guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from event_classification import Classification, Disposition

# Petition dates disclosed by different filings for the same case occasionally
# differ by a day or two, usually a filing-time versus docketing-time gap.
MERGE_DAY_TOLERANCE = 3

# How long after an event an amendment can arrive and still be assumed to
# describe it when it carries no date of its own.
AMENDMENT_WINDOW_DAYS = 120


@dataclass
class BankruptcyEvent:
    """One bankruptcy, with every filing that described it."""

    cik: int
    disposition: Disposition
    petition_date: date | None = None
    court: str | None = None
    docket: str | None = None
    first_disclosed_at: datetime | None = None
    source_accessions: list[str] = field(default_factory=list)
    # Set when an 8-K/A that explicitly corrects the petition date replaced it.
    petition_date_corrected: bool = False
    # The initial petition's chapter (LABEL_POLICY 5): set by the first positive
    # source and never overwritten by a later conversion.
    chapter: int | None = None
    # Metadata only: some source stated an actual conversion to Chapter 7.
    converted_to_chapter_7: bool = False

    @property
    def event_at(self) -> datetime | None:
        """Canonical event time: the petition date, never the disclosure date."""
        if self.petition_date is None:
            return None
        return datetime.combine(self.petition_date, datetime.min.time())

    @property
    def is_positive(self) -> bool:
        return self.disposition.is_positive

    @property
    def is_fully_identified(self) -> bool:
        """Both identity fields present, so no amendment can add to them."""
        return self.petition_date is not None and self.docket is not None

    def absorb(self, classification: Classification, accession: str,
               disclosed_at: datetime, is_amendment: bool = False) -> None:
        """Merge another filing's information into this event.

        Fields fill from whichever source first supplies them, with one
        exception (LABEL_POLICY 10): an 8-K/A that explicitly corrects the
        petition date REPLACES the earlier value. Fill-if-null alone meant an
        amendment could supply a missing date but never fix a wrong one, so
        Proxim kept the year its own /A called a scrivener's error, and Brooke
        Capital kept the date its /A was filed specifically to correct.
        """
        self.source_accessions.append(accession)
        corrected = getattr(classification, "corrected_petition_date", None)
        if (is_amendment and getattr(classification, "corrects_petition_date", False)
                and corrected is not None and corrected != self.petition_date):
            self.petition_date = corrected
            self.petition_date_corrected = True
        self.petition_date = self.petition_date or classification.petition_date
        self.court = self.court or classification.court
        self.docket = self.docket or classification.docket
        if classification.disposition.is_positive and not self.disposition.is_positive:
            self.disposition = classification.disposition
            self.chapter = getattr(classification, "chapter", None)
        if self.chapter is None and self.disposition.is_positive:
            self.chapter = getattr(classification, "chapter", None)
        self.converted_to_chapter_7 = self.converted_to_chapter_7 or bool(
            getattr(classification, "converted_to_chapter_7", False)
        )
        if self.first_disclosed_at is None or disclosed_at < self.first_disclosed_at:
            self.first_disclosed_at = disclosed_at


def assemble_events(
    cik: int, sources: list[tuple[str, datetime, Classification, bool]]
) -> list[BankruptcyEvent]:
    """Cluster one CIK's Item 1.03 filings into distinct bankruptcy events.

    Each source is (accession, disclosure time, classification, is_amendment).
    The amendment flag is load-bearing: the whole reason amendments are kept is
    that one can supply the petition date or docket its original omitted, and
    that case is unmatchable by identity alone precisely because the original
    has no identity yet.
    """
    events: list[BankruptcyEvent] = []

    for accession, disclosed_at, classification, is_amendment in sorted(
        sources, key=lambda source: source[1]
    ):
        match = _find_match(events, classification, disclosed_at, is_amendment)
        if match is None:
            match = BankruptcyEvent(cik=cik, disposition=classification.disposition)
            events.append(match)
        match.absorb(classification, accession, disclosed_at, is_amendment)

    return events


def _find_match(
    events: list[BankruptcyEvent],
    classification: Classification,
    disclosed_at: datetime,
    is_amendment: bool,
) -> BankruptcyEvent | None:
    for event in events:
        if _dockets_agree(classification, event):
            return event
        if _petition_dates_agree(classification, event):
            return event
        if _same_case_across_chapters(classification, event):
            return event
        if is_amendment and _amends(event, classification, disclosed_at):
            return event
    return None


def _dockets_agree(classification: Classification, event: BankruptcyEvent) -> bool:
    return bool(
        classification.docket and event.docket and classification.docket == event.docket
    )


def _petition_dates_agree(
    classification: Classification, event: BankruptcyEvent
) -> bool:
    if not classification.petition_date or not event.petition_date:
        return False
    if classification.disposition != event.disposition:
        return False
    return (
        abs((classification.petition_date - event.petition_date).days)
        <= MERGE_DAY_TOLERANCE
    )


def _same_case_across_chapters(
    classification: Classification, event: BankruptcyEvent
) -> bool:
    """A Chapter 7 record and a Chapter 11 record that are provably one case.

    Matching dockets are handled before this. Otherwise requires the EXACT same
    petition date plus one piece of same-case evidence: a stated conversion, or
    the same bankruptcy court. Date tolerance alone never merges across chapters.
    """
    if not (classification.disposition.is_positive and event.disposition.is_positive):
        return False
    if classification.disposition == event.disposition:
        return False
    if classification.petition_date is None or classification.petition_date != event.petition_date:
        return False
    converted = bool(getattr(classification, "converted_to_chapter_7", False)) \
        or event.converted_to_chapter_7
    same_court = bool(classification.court and event.court and classification.court == event.court)
    return converted or same_court


def _amends(
    event: BankruptcyEvent, classification: Classification, disclosed_at: datetime
) -> bool:
    """Can this /A filing be completing an event that is still half-identified?

    Requires the event to be missing identity information, so a fully
    identified event is never absorbed by proximity alone.
    """
    if event.is_fully_identified or event.first_disclosed_at is None:
        return False
    if disclosed_at - event.first_disclosed_at > timedelta(days=AMENDMENT_WINDOW_DAYS):
        return False
    if not _dispositions_compatible(classification.disposition, event.disposition):
        return False
    return not (
        classification.court and event.court and classification.court != event.court
    )


def _dispositions_compatible(incoming: Disposition, existing: Disposition) -> bool:
    """Identical, or one side is still unresolved."""
    return (
        incoming == existing
        or Disposition.AMBIGUOUS in {incoming, existing}
    )
