"""Filing history from the SEC bulk submissions archive.

The per-company submissions endpoint returns only the most recent slice of a
filer's history in `filings.recent`; everything older sits in the auxiliary
files listed under `filings.files`. Querying only `recent` makes a 2012
predecessor 10-K invisible and silently marks the event unlabelable, which
biases the usable-event count downward exactly in the early cohorts.

Reading the bulk archive avoids that and also avoids one network round trip per
event. Download it once:

    https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip

VERIFY that URL against the live SEC bulk data listing before relying on it.

Timestamps here are EDGAR acceptance datetimes, not filing dates. The study
defines its point-in-time cutoff on acceptance, so the eligibility check has to
use the same clock.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from pathlib import Path

# SIC 6000-6799 is the whole Finance, Insurance and Real Estate block, not just
# banks. Excluding all of it is a deliberate choice about accounting structure
# and distress mechanics, and the paper must say so in those words rather than
# calling it a "financial institution" exclusion.
FIRE_SIC_RANGE = (6000, 6799)

# Filings whose acceptance falls after 17:30 ET are disseminated the next
# business day. Immaterial for a 365-day window, material for any intraday
# claim; noted so nobody reuses this helper for one.
DISSEMINATION_CUTOFF_NOTE = "acceptance after 17:30 ET disseminates next day"

# A filing made shortly after a name change may still use the other name.
NAME_GRACE_DAYS = 90


@dataclass(frozen=True)
class TenKFiling:
    """A 10-K submission and the classification attached to it AT FILING TIME.

    `sic_as_filed` is deliberately not populated from the company's present-day
    profile. The submissions archive carries only a current SIC, and using it
    would leak a 2026 classification backward onto a 2013 observation, which is
    the exact class of error the study exists to measure. The per-submission
    SIC lives in the DERA Financial Statement Data Sets `sub` table and is
    joined in there.
    """

    accession: str
    accepted_at: datetime
    sic_as_filed: int | None = None


@dataclass(frozen=True)
class CompanyProfile:
    """Filing history for one CIK.

    The observational unit of the whole study is a registrant identified by
    CIK. No parent-child resolution is attempted: a subsidiary filing that the
    registrant is not party to is simply not this registrant's event. Corporate
    family structure across fifteen years of mergers and spin-offs is a
    different research problem, not a preprocessing step.
    """

    cik: int
    current_sic: int | None
    entity_type: str | None
    tenk_filings: tuple[TenKFiling, ...]
    # EDGAR names with their validity: (name, from, to), `to` None for the current
    # name. Used only to recognise the registrant in its own filings' text.
    name_history: tuple[tuple[str, datetime | None, datetime | None], ...] = ()

    def names_at(self, when: datetime) -> tuple[str, ...]:
        """The registrant's EDGAR names in effect when a filing was accepted.

        Point-in-time: a name adopted later is not used to read an earlier filing
        (GenOn Mid-Atlantic was Mirant Mid-Atlantic in 2005), and a name given up
        years before is not used either -- a subsidiary may carry it by then (DRI
        Corporation, formerly Digital Recorders, listed "Digital Recorders, Inc."
        as a subsidiary in 2012). NAME_GRACE_DAYS covers filings made just
        after a change that still use the other name.
        """
        grace = timedelta(days=NAME_GRACE_DAYS)
        return tuple(
            name
            for name, start, end in self.name_history
            if (start is None or start - grace <= when) and (end is None or when <= end + grace)
        )


class SicEligibility(str, Enum):
    """Three outcomes, because missing SIC cannot mean "not FIRE".

    Treating an unknown SIC as eligible lets excluded industries leak back in
    through missingness, and that missingness will not be random. Unknown is
    its own census bucket and is excluded from the primary benchmark.
    """

    ELIGIBLE = "eligible"
    FIRE_EXCLUDED = "fire_excluded"
    UNKNOWN = "unknown_sic"


def classify_sic(sic: int | None) -> SicEligibility:
    """Finance, Insurance and Real Estate exclusion, by SIC as filed."""
    if sic is None:
        return SicEligibility.UNKNOWN
    low, high = FIRE_SIC_RANGE
    if low <= sic <= high:
        return SicEligibility.FIRE_EXCLUDED
    return SicEligibility.ELIGIBLE


class SubmissionsArchive:
    """Random access to complete filing histories inside the bulk zip.

    Takes the DERA accession-to-SIC index so every 10-K carries the industry
    classification it had at submission time. Without it `sic_as_filed` is None
    everywhere and the FIRE exclusion silently excludes nothing.
    """

    def __init__(self, archive_path: Path, sic_index: dict[str, int] | None = None):
        self._archive = zipfile.ZipFile(archive_path)
        self._names = set(self._archive.namelist())
        self._sic_index = sic_index or {}

    @lru_cache(maxsize=4096)
    def profile(self, cik: int) -> CompanyProfile | None:
        primary_name = f"CIK{cik:010d}.json"
        if primary_name not in self._names:
            return None

        primary = self._read(primary_name)
        filings = primary.get("filings", {})
        blocks = [filings.get("recent", {})]
        for extra in filings.get("files", []):
            extra_name = extra.get("name")
            if extra_name in self._names:
                blocks.append(self._read(extra_name))

        return CompanyProfile(
            cik=cik,
            current_sic=_parse_int(primary.get("sic")),
            entity_type=primary.get("entityType"),
            name_history=_name_history(primary),
            tenk_filings=tuple(
                sorted(
                    (
                        filing
                        for block in blocks
                        for filing in _extract_tenk_filings(block, self._sic_index)
                    ),
                    key=lambda filing: filing.accepted_at,
                )
            ),
        )

    def _read(self, name: str) -> dict:
        with self._archive.open(name) as handle:
            return json.loads(handle.read().decode("utf-8"))


def find_predecessor_tenk(
    profile: CompanyProfile, event_at: datetime, horizon_days: int
) -> TenKFiling | None:
    """The latest 10-K accepted within the horizon ending at the event.

    Returns the latest rather than the earliest: if a firm filed twice inside
    the window, the most recent filing is the one whose information set a
    real-time model would have used.
    """
    window_start = event_at - timedelta(days=horizon_days)
    eligible = [
        filing
        for filing in profile.tenk_filings
        if window_start < filing.accepted_at < event_at
    ]
    return eligible[-1] if eligible else None


def _extract_tenk_filings(
    block: dict, sic_index: dict[str, int]
) -> list[TenKFiling]:
    forms = block.get("form", [])
    accessions = block.get("accessionNumber", [])
    accepted = block.get("acceptanceDateTime", [])
    filed = block.get("filingDate", [])

    filings: list[TenKFiling] = []
    for index, form in enumerate(forms):
        if form != "10-K":
            continue
        timestamp = _parse_timestamp(
            accepted[index] if index < len(accepted) else None,
            filed[index] if index < len(filed) else None,
        )
        if timestamp is None:
            continue
        accession = accessions[index]
        filings.append(
            TenKFiling(
                accession=accession,
                accepted_at=timestamp,
                sic_as_filed=sic_index.get(accession),
            )
        )
    return filings


def _name_history(primary: dict) -> tuple[tuple[str, datetime | None, datetime | None], ...]:
    """Current name valid from the end of the latest former name; former names
    valid over their own from/to window."""
    former = [
        (
            item["name"],
            _parse_timestamp(item.get("from"), None),
            _parse_timestamp(item.get("to"), None),
        )
        for item in primary.get("formerNames", []) or []
        if item.get("name")
    ]
    ends = [end for _, _, end in former if end is not None]
    current = primary.get("name")
    history = [(current, max(ends) if ends else None, None)] if current else []
    return tuple(history + former)


def _parse_timestamp(accepted: str | None, filed: str | None) -> datetime | None:
    """Prefer the acceptance timestamp; fall back to the filing date.

    Any fallback should be counted and reported, since it means the observation
    is timed less precisely than the point-in-time contract requires.
    """
    if accepted:
        try:
            return datetime.fromisoformat(accepted.replace("Z", "+00:00")).replace(
                tzinfo=None
            )
        except ValueError:
            pass
    if filed:
        try:
            return datetime.fromisoformat(filed)
        except ValueError:
            return None
    return None


def _parse_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
