"""Classify Item 1.03 candidates into the outcome the study actually labels.

Item 1.03 is "Bankruptcy or Receivership". The study's label is narrower: the
registrant itself entering Chapter 7 or Chapter 11. Three things live under the
same item code and must be separated:

  - the registrant files a Chapter 7 or Chapter 11 petition          POSITIVE
  - a subsidiary or affiliate files and the registrant does not      NOT POSITIVE
  - a receiver is appointed, e.g. an FDIC bank receivership          NOT POSITIVE

Rules, not a model. Rules are auditable, cheap, and their failure modes are
legible. They are also not exact, which is why anything the rules cannot
resolve lands in AMBIGUOUS rather than being forced into a bucket. Gate 1 then
reports a bounded count, and Gate 2 runs at both bounds.

Every rule threshold here is a guess until a hand-labelled sample says
otherwise. Validate on at least 100 randomly drawn candidates before the output
gates anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date
from enum import Enum

from constants import BANKRUPTCY_ITEM_CODE


class Disposition(str, Enum):
    REGISTRANT_CHAPTER_7 = "registrant_chapter_7"
    REGISTRANT_CHAPTER_11 = "registrant_chapter_11"
    SUBSIDIARY_ONLY = "subsidiary_only"
    RECEIVERSHIP_ONLY = "receivership_only"
    AMBIGUOUS = "ambiguous"

    @property
    def is_positive(self) -> bool:
        return self in {
            Disposition.REGISTRANT_CHAPTER_7,
            Disposition.REGISTRANT_CHAPTER_11,
        }


@dataclass(frozen=True)
class Classification:
    """What the Item 1.03 section says, parsed into study terms.

    `petition_date` is the canonical event time. The 8-K acceptance timestamp
    is a disclosure time and can sit days later; substituting it silently
    lengthens the prediction horizon, and disclosure delay is unlikely to be
    benign in the delinquent issuers that supply the positive class.
    """

    disposition: Disposition
    petition_date: date | None
    court: str | None
    docket: str | None
    matched_rules: tuple[str, ...]
    # Where the classified text came from: "item_1_03" (a substantive Item 1.03
    # body), "legacy_item_3" (pre-2004 numbering), or "fallback" (no substantive
    # section; the whole primary filing was read under conservative rules).
    section_source: str = "item_1_03"
    # The filing states that it corrects the bankruptcy/petition date. Read from
    # the whole document, because the correction usually sits in an explanatory
    # note ahead of Item 1.03. Only honoured for 8-K/A sources (LABEL_POLICY 10).
    corrects_petition_date: bool = False
    # When it does, the date stated in the petition-filing sentence. Deliberately
    # NOT the first date in the section: a correcting 8-K/A usually opens by
    # citing the date of the report it amends ("amends the Form 8-K filed on
    # October 29, 2008"), and that report date must never become the petition
    # date (LABEL_POLICY 8).
    corrected_petition_date: date | None = None
    # The chapter of the INITIAL petition (LABEL_POLICY 1, 5, 6): taken from the
    # registrant's petition sentence, never from a conversion target, a
    # conversion motion, DIP events-of-default boilerplate or risk language.
    chapter: int | None = None
    # Metadata only: the filing states an ACTUAL conversion to Chapter 7. A later
    # conversion is not a new event and does not change `chapter`.
    converted_to_chapter_7: bool = False

    @property
    def has_strong_identity(self) -> bool:
        return self.court is not None and self.docket is not None


# Item headings as they appear in 8-K bodies. Classification runs on the
# Item 1.03 section alone: an 8-K can mention a prior Chapter 11, an affiliate
# proceeding, or a historical case elsewhere in the document and trip the rules.
ITEM_HEADING = re.compile(r"^\s*Item\s+(\d\.\d{2})\b", re.IGNORECASE | re.MULTILINE)

CHAPTER_7 = re.compile(r"\bchapter\s*7\b", re.IGNORECASE)
CHAPTER_11 = re.compile(r"\bchapter\s*11\b", re.IGNORECASE)
RECEIVERSHIP = re.compile(
    r"\b(receiver|receivership|conservator|FDIC as receiver)\b", re.IGNORECASE
)

# Form 8-K's own name for Item 1.03. It is a HEADING, not evidence.
#
# `extract_item_section` slices from the end of the "Item 1.03" match, so the
# title that follows it lands inside the classified text. RECEIVERSHIP then
# matched the word "Receivership" in that title on essentially every Item 1.03
# filing, and because the receivership branch is reached whenever no chapter is
# named, filings that merely omitted the literal string "chapter 7"/"chapter 11"
# were recorded as receiverships. Measured on the real corpus: 910 of 1,094
# such filings had NO "receiver*" anywhere except the first 40 characters.
#
# Stripping the title also restores the no-chapter/no-receivership AMBIGUOUS
# branch, which was unreachable while every section carried the word.
#
# Variants observed in real filings are matched too, because a surviving variant
# re-triggers exactly the defect above: the plural "BANKRUPTCIES OR RECEIVERSHIP",
# the typo "Bankruptcy of Receivership", "Bankruptcy and Receivership", and the
# misspellings "Recievership" / "Receivorship".
ITEM_TITLE = re.compile(
    r"Bankruptc(?:y|ies)\s*(?:or|of|and|&)\s*Rec(?:ei|ie)v(?:er|or)ships?", re.IGNORECASE
)

# Pre-August-2004 Form 8-K numbered this item "Item 3". Some filers kept the old
# numbering later. Only accepted when the bankruptcy title follows, so the "Item
# 3" of any other form or list is never mistaken for it.
LEGACY_BANKRUPTCY_HEADING = re.compile(
    r"^\s*Item\s+3\b[\s.:\-–—]*(?=Bankruptc(?:y|ies)\s*(?:or|of|and|&)\s*Rec)",
    re.IGNORECASE | re.MULTILINE,
)

# A table-of-contents or index entry for an item is its title followed by nothing,
# or by navigation text. Such a stub is NOT the item's disclosure.
_NAVIGATION_START = re.compile(
    r"^(?:signatures?\b|table\s+of\s+contents\b|index\b|exhibit\s+index\b|page\s+\d|"
    r"item\s+\d|section\s+\d|\d{1,3}\s*$)",
    re.IGNORECASE,
)

# Entity suffixes whose full stop is punctuation inside a name, not a sentence
# boundary. Identity rules are sentence-bounded so a rule cannot leap across
# sentences; an embedded "Inc." defeated that, e.g.
# "the Company and Specialty Retailers, Inc. filed voluntary petitions".
# Measured: 203 of 751 AMBIGUOUS filings carry this construction.
#
# Normalising the known suffixes keeps the sentence bound intact rather than
# loosening it. Widening [^.] to allow periods would let the rule cross real
# sentence boundaries and match a registrant in one sentence against a
# subsidiary's filing in the next, which is a worse error than the one fixed.
_LEGAL_ABBREVIATIONS = (
    # Dotted multi-letter forms first, so "L.L.C." is not left as "LLC." below.
    (re.compile(r"\bL\.\s?L\.\s?C\.", re.IGNORECASE), "LLC"),
    (re.compile(r"\bL\.\s?L\.\s?P\.", re.IGNORECASE), "LLP"),
    (re.compile(r"\bL\.\s?P\.", re.IGNORECASE), "LP"),
    (re.compile(r"\bP\.\s?L\.\s?C\.", re.IGNORECASE), "PLC"),
    (re.compile(r"\bS\.\s?p\.\s?A\.", re.IGNORECASE), "SpA"),
    (re.compile(r"\bN\.\s?V\.", re.IGNORECASE), "NV"),
    (re.compile(r"\bS\.\s?A\.\s?B\.", re.IGNORECASE), "SAB"),
    (re.compile(r"\bS\.\s?A\.", re.IGNORECASE), "SA"),
    (re.compile(r"\bA\.\s?G\.", re.IGNORECASE), "AG"),
    (re.compile(r"\bA\.\s?S\.", re.IGNORECASE), "AS"),
    # Single-token suffixes: drop only the trailing full stop.
    (
        re.compile(
            r"\b(Inc|Corp|Co|Ltd|LLC|LLP|LP|PLC|Pte|Pty|Bhd|GmbH|AG|NV|SA|Cia|Cie|"
            r"Sdn|Oy|AB|AS|Holdings?|Cos)\.",
            re.IGNORECASE,
        ),
        r"\1",
    ),
)

# Language that scopes the filing to entities other than the registrant.
SUBSIDIARY_SCOPED = re.compile(
    r"\b(certain|its|our)\s+(direct\s+|indirect\s+|wholly[- ]owned\s+)?"
    r"(subsidiar(y|ies)|affiliates?)\b",
    re.IGNORECASE,
)

# Every date shape demonstrated in the development audit: month-first with an
# optional weekday ("On Friday, April 30, 2010"), ordinal ("March 25th, 2005"),
# missing comma ("October 7 2011") or missing space ("August11, 2014"), a compound
# day pair ("March 26 and 27, 2009"), and day-first ("24 September 2014").
_MONTH_NAME = (
    r"January|February|March|April|May|June|July|August|September|October|November|"
    r"December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
)
_ORDINAL = r"(?:st|nd|rd|th)?"
DATE_MENTION = re.compile(
    r"\b(?:(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,?\s*)?(?:"
    rf"(?P<m1>{_MONTH_NAME})\.?\s*(?P<d1>\d{{1,2}}){_ORDINAL}(?!\d)"
    rf"(?P<second>\s*(?:and|&)\s*\d{{1,2}}{_ORDINAL})?,?\s*(?P<y1>(?:19|20)\d\d)"
    rf"|(?P<d2>\d{{1,2}}){_ORDINAL}\s+(?P<m2>{_MONTH_NAME})\.?,?\s+(?P<y2>(?:19|20)\d\d)"
    r")(?!\d)",
    re.IGNORECASE,
)

# "the United States Bankruptcy Court for the District of Delaware"
COURT = re.compile(
    r"United\s+States\s+Bankruptcy\s+Court\s+for\s+the\s+"
    r"((?:Northern|Southern|Eastern|Western|Central|Middle)?\s*"
    r"District\s+of\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)",
)

# "Case No. 24-11390" or "Case Nos. 24-11390 (JTD)"
DOCKET = re.compile(r"\bCase\s+Nos?\.?\s*([0-9]{2}[-\u2013][0-9]{3,6})", re.IGNORECASE)

MONTHS_BY_PREFIX = {
    name[:3].lower(): number
    for number, name in enumerate(
        (
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ),
        start=1,
    )
}

def extract_item_section(document_text: str, item_code: str) -> str:
    """The text of one 8-K item: see `locate_item_section`."""
    return locate_item_section(document_text, item_code)[0]


def locate_item_section(document_text: str, item_code: str) -> tuple[str, str]:
    """The substantive body of one 8-K item, and where it came from.

    Returns (text, source), source being "item_1_03", "legacy_item_3" or
    "fallback".

    The FIRST textual occurrence of the heading is not trusted. Filings with a
    table of contents or cover index repeat every item title near the top, and
    taking that occurrence classified the index instead of the disclosure: one
    filing's slice was literally ". .", another's was the index tail plus
    forward-looking boilerplate, which lost the petition date. Each candidate
    heading is therefore tested, and the first whose body is not an index stub
    is used.

    When no substantive body exists, the whole primary filing is returned with
    source "fallback", and `classify` applies conservative rules to it rather
    than treating a stub as the section.
    """
    headings = [(m.start(), m.end(), m.group(1), "item_1_03")
                for m in ITEM_HEADING.finditer(document_text)]
    if item_code == BANKRUPTCY_ITEM_CODE:
        headings += [(m.start(), m.end(), item_code, "legacy_item_3")
                     for m in LEGACY_BANKRUPTCY_HEADING.finditer(document_text)]
    headings.sort()
    for position, (start, body_start, code, source) in enumerate(headings):
        if code != item_code:
            continue
        end = next(
            (other_start for other_start, _, _, _ in headings[position + 1:]
             if other_start > start),
            len(document_text),
        )
        body = strip_item_title(document_text[body_start:end])
        if not _is_index_stub(body):
            return body, source
    return strip_item_title(document_text), "fallback"


def _is_index_stub(body: str) -> bool:
    """A title with nothing after it, or with navigation text after it."""
    lead = re.sub(r"^[\s.:;,\-–—()\[\]\xa0]+", "", body)
    if not re.search(r"[A-Za-z]{2}", lead):
        return True
    return bool(_NAVIGATION_START.match(lead[:60]))


def strip_item_title(section_text: str) -> str:
    """Remove Form 8-K's own name for Item 1.03 from the text to be classified.

    The title is the form's boilerplate, not a statement about this filing, so
    no rule may read evidence out of it. Applied to the fallback path too: when
    no heading is found the whole document is classified, and the title is then
    sitting in the middle of it.
    """
    return ITEM_TITLE.sub(" ", section_text)


def normalize_legal_abbreviations(text: str) -> str:
    """Strip the full stops out of entity suffixes, leaving sentences intact.

    Purely a punctuation normalisation for matching: no word is added, removed
    or reordered, so it cannot create evidence that the filing does not contain.
    """
    for pattern, replacement in _LEGAL_ABBREVIATIONS:
        text = pattern.sub(replacement, text)
    return text


def classify(
    document_text: str,
    item_code: str = BANKRUPTCY_ITEM_CODE,
    registrant_names: tuple[str, ...] = (),
    co_registered: bool = False,
) -> Classification:
    """Assign a disposition, reading only the relevant item section.

    `registrant_names` are the filer's EDGAR names (current and former) used to
    recognise the registrant when the text names it rather than calling it "the
    Company". `co_registered` marks a filing submitted under several CIKs: there a
    generic "the Company" may denote another registrant, so a positive needs the
    exact name (LABEL_POLICY 11).
    """
    corrects = states_petition_date_correction(document_text)
    full_text = normalize_legal_abbreviations(document_text)
    ctx = _IdentityContext(
        name_patterns=tuple(
            (built[0], built[1], position > 0, built[2])
            for position, built in enumerate(map(_name_pattern, registrant_names))
            if built is not None
        ),
        co_registered=co_registered,
        full_text=" ".join(full_text.split()),
    )
    section, source = locate_item_section(document_text, item_code)
    document_text = normalize_legal_abbreviations(section)

    if source == "fallback":
        # The filing declared Item 1.03 but no substantive Item 1.03 body could be
        # extracted, so the whole primary filing is being read. Other items can
        # mention an affiliate's case, a historical Chapter 11, a lender's
        # receivership, so nothing outside a strong statement is trusted: only
        # sentences carrying an actual registrant filing clause AND a Chapter
        # 7/11 reference are classified. Without one, the filing is AMBIGUOUS --
        # never receivership-only or subsidiary-only on fallback text.
        strong = _strong_filing_sentences(document_text, ctx)
        if not strong:
            return Classification(
                Disposition.AMBIGUOUS, None, None, None, ("section:fallback",),
                "fallback", corrects, None,
            )
        document_text = " ".join(strong)

    result = _classify_text(document_text, full_text, ctx)
    # replace() carries every field _classify_text set (chapter, conversion
    # metadata, ...) instead of rebuilding positionally and silently dropping any.
    return replace(
        result,
        matched_rules=(f"section:{source}",) + result.matched_rules,
        section_source=source,
        corrects_petition_date=corrects,
        corrected_petition_date=(
            _extract_petition_date(document_text, full_text, ctx) if corrects else None
        ),
    )


_FILING_VERB = re.compile(r"\b(?:filed|commenced|initiated)\b", re.IGNORECASE)
_PETITION_OBJECT = re.compile(
    r"\b(?:petitions?|protection|chapter\s*(?:7|11)|cases?|proceedings?)\b", re.IGNORECASE
)


_CORRECTION_WORD = re.compile(r"\b(?:correct(?:s|ed|ing|ly|ion)?|scrivener)", re.IGNORECASE)
_CORRECTION_OBJECT_DATE = re.compile(r"\bdates?\b", re.IGNORECASE)
_CORRECTION_OBJECT_EVENT = re.compile(
    r"\b(?:petitions?|bankruptcy|chapter\s*(?:7|11)|filed|filing)\b", re.IGNORECASE
)


def states_petition_date_correction(document_text: str) -> bool:
    """Does the filing say it corrects the date of the bankruptcy filing?

    Real forms: "This amended Form 8-K correctly states the dates of the
    bankruptcy filing" (one sentence), and "...in order to correct a scrivener's
    error in Item 1.03. The date on which the Company ... filed voluntary
    petitions ... was June 11, 2005, not June 11, 2004" (correction sentence
    followed by the corrected-date sentence). A correction word must meet a date
    reference and a bankruptcy-filing reference within that two-sentence span.
    """
    text = " ".join(normalize_legal_abbreviations(document_text).split())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for position, sentence in enumerate(sentences):
        if not _CORRECTION_WORD.search(sentence):
            continue
        span = sentence + " " + (sentences[position + 1] if position + 1 < len(sentences) else "")
        if _CORRECTION_OBJECT_DATE.search(span) and _CORRECTION_OBJECT_EVENT.search(span):
            return True
    return False


_SENTENCE_ABBREVIATION = re.compile(r"\b(No|Nos|Mr|Ms|Mrs|Dr|St|Jr|Sr|vs|v|al|U\.S|U\.S\.A)\.")
_CHAPTER = re.compile(r"\bchapter\s*(7|11)\b", re.IGNORECASE)
_CONVERT = re.compile(r"\bconver(?:t|ts|ted|ting|sion)\b", re.IGNORECASE)
_CONVERSION_JOIN = re.compile(r"\b(?:to|into)\b", re.IGNORECASE)
_INVOLUNTARY_OR_RELIEF = re.compile(
    r"\binvoluntary\s+petitions?\b|\bseeking\s+relief\s+under\b", re.IGNORECASE
)
# Language that makes a Chapter 7 mention hypothetical, conditional, or a default
# trigger rather than a filed case. "may" is matched lower-case only, so the
# month "May" never counts.
_CHAPTER_7_NON_EVENT = re.compile(
    r"\b(?:defaults?|termination\s+events?|in\s+the\s+event|if|unless|might|could|would|"
    r"should|risks?|forward-looking|no\s+assurance|whether|possib\w*|potential\w*|"
    r"contemplat\w*|seek\w*|motion|intend\w*|expect\w*|anticipat\w*|propos\w*)\b"
    r"|(?-i:\bmay\b)",
    re.IGNORECASE,
)
_ACTUAL_CONVERSION = re.compile(
    r"\b(?:was|were|has\s+been|have\s+been)\s+converted\b|\bconverted\s+the\b|"
    r"\b(?:entered|issued)\s+an\s+order\s+converting\b|\bgranted\b[^.]{0,120}\bconver",
    re.IGNORECASE,
)


# Date ranking additionally keeps single-letter initials and "et seq." inside
# their sentence: "11 U.S.C. §§ 101 et seq. (the Code) ... on March 16, 2017" and
# "GameTech Mexico, S. de R.L. de C.V. filed voluntary petitions" were cut in two,
# as were "Mt. Waimea, Inc" debtor lists and "2:00 p.m. Pacific Time",
# separating the date from its petition. Kept separate from the chapter
# splitter so this stage does not move any disposition.
_DATE_SENTENCE_ABBREVIATION = re.compile(
    r"\b(No|Nos|Mr|Ms|Mrs|Dr|St|Mt|Jr|Sr|vs|v|al|U\.S|U\.S\.A|seq|[A-Za-z])\."
)


def _split_sentences(
    text: str, abbreviations: re.Pattern[str] = _SENTENCE_ABBREVIATION
) -> list[str]:
    """Split into sentences without breaking at "Case No.", "U.S.", "Mr." and similar."""
    masked = abbreviations.sub(lambda m: m.group(1).replace(".", "\x00") + "\x00", text)
    parts = re.split(r"(?<=[.!?])\s+", " ".join(masked.split()))
    return [part.replace("\x00", ".") for part in parts if part]


def _chapter_mentions(sentence: str) -> list[tuple[int, int, bool]]:
    """(chapter, position, is_conversion_target) for each Chapter 7/11 mention.

    A mention is a conversion TARGET when a convert/conversion word precedes it
    with "to"/"into" in between: in "convert the Chapter 7 proceeding ... to a
    Chapter 11 proceeding" the 7 is the case as filed and the 11 is the target.
    """
    mentions = []
    for match in _CHAPTER.finditer(sentence):
        before = sentence[: match.start()]
        converts = list(_CONVERT.finditer(before))
        is_target = bool(converts) and bool(_CONVERSION_JOIN.search(before[converts[-1].end():]))
        mentions.append((int(match.group(1)), match.start(), is_target))
    return mentions


def _is_petition_sentence(sentence: str) -> bool:
    return bool(
        (_FILING_VERB.search(sentence) and _PETITION_OBJECT.search(sentence))
        or _INVOLUNTARY_OR_RELIEF.search(sentence)
    )


_CONDITIONAL = re.compile(r"\b(?:if|will|would)\b", re.IGNORECASE)


def _states_actual_conversion_to_7(sentence: str, mentions: list[tuple[int, int, bool]]) -> bool:
    """A conversion to Chapter 7 that happened, not one sought, proposed or conditional."""
    targets_7 = any(chapter == 7 and target for chapter, _, target in mentions)
    return bool(
        targets_7 and _ACTUAL_CONVERSION.search(sentence) and not _CONDITIONAL.search(sentence)
    )


def _initial_chapter(
    text: str, ctx: _IdentityContext | None = None
) -> tuple[int | None, bool]:
    """The chapter of the initial petition, and whether an actual 11->7 conversion is stated.

    Priority, earliest sentence first within each tier:
      1. a petition sentence in which the registrant is a filing party
      2. any other petition sentence
      3. any other sentence
    Conversion targets never count. In tiers 2-3 a Chapter 7 mention in a
    hypothetical, conditional, default or motion sentence does not count either.
    Tier 1 is anchored by the registrant's own filing verb, so it is exempt:
    a Chapter 7 petition sentence can legitimately mention a trustee who "may" act.
    """
    sentences = _split_sentences(text)
    converted = False
    tiers: list[list[int]] = [[], [], []]
    for sentence in sentences:
        mentions = _chapter_mentions(sentence)
        if _states_actual_conversion_to_7(sentence, mentions):
            converted = True
        eligible = [(pos, ch) for ch, pos, target in mentions if not target]
        if not eligible:
            continue
        petition = _is_petition_sentence(sentence)
        if petition and _registrant_is_debtor_in(sentence, ctx):
            tiers[0].append(min(eligible)[1])
            continue
        hypothetical = bool(_CHAPTER_7_NON_EVENT.search(sentence))
        kept = [(pos, ch) for pos, ch in eligible if not (ch == 7 and hypothetical)]
        if kept:
            tiers[1 if petition else 2].append(min(kept)[1])
    for tier in tiers:
        if tier:
            return tier[0], converted
    return None, converted


# ---------------------------------------------------------------------------
# Registrant identity (repair stage 5: mechanisms A1-A5, F, G; LABEL_POLICY 1,
# 4, 11).
#
# The old rules asked whether a registrant TOKEN and the noun "petition" sat
# within 120 characters of a filing verb. That missed "commenced voluntary
# cases" and "filed for bankruptcy protection" (A1), "we", "the Debtors" and
# the registrant's own name (A2), `the Company") and certain of its` (A3), long
# debtor lists (A4) and "U.S. subsidiaries" (A5); and it let a subsidiary's
# petition through whenever the parent's defined term sat in the apposition (F)
# or the filing was only planned or denied (G).
#
# Identity is now read clause by clause. A FILING CLAUSE is an actual, past
# filing: a filing verb whose first object is a bankruptcy petition, case,
# proceeding or protection, with Chapter 7/11 or bankruptcy language in the
# same sentence, or an involuntary petition against a named party. Its PARTIES
# are the subject span before the verb (or the target of "against" / "In re").
# The registrant is a party only through a reference that is not the parent in
# a "subsidiary of" apposition, a possessive ("the Registrant's subsidiary"), or
# the beneficiary of "filed ... for its subsidiaries". Anything the clause
# cannot settle is AMBIGUOUS, never positive.
#
# Every lexical cue below is word-bounded, and cues that also occur in proper
# names (motion, plan, vote, convert, approve) are matched lower-case only, so
# "T3 Motion, Inc." or "FCP VoteCo" cannot act as event words.
# ---------------------------------------------------------------------------

_NAME_SUFFIX_TOKENS = frozenset({
    "inc", "incorporated", "corp", "corporation", "co", "company", "llc", "lp", "llp",
    "ltd", "limited", "plc", "sa", "nv", "ag", "the", "l", "p", "de",
})
_ENTITY_SUFFIX_WORD = (
    r"(?:Inc|Incorporated|Corp|Corporation|Co|Company|LLC|LP|LLP|Ltd|Limited|plc|PLC|SA|NV|AG)"
)
# Suffix equivalence: "Nortel Networks Corp" is "Nortel Networks Corporation" but
# not the subsidiary "Nortel Networks Inc".
_SUFFIX_CLASS = {
    "inc": "inc", "incorporated": "inc", "corp": "corp", "corporation": "corp",
    "co": "co", "company": "co", "llc": "llc", "lp": "lp", "llp": "llp",
    "ltd": "ltd", "limited": "ltd", "plc": "plc", "sa": "sa", "nv": "nv", "ag": "ag",
}

# Generic self-references. "Corporation", "Partnership" and "Trust" count only
# as a capitalised defined term after "the": "a Nevada corporation" is not one.
# A bare "Company" is not one: "Appalachian Oil Company, Inc." is a name.
_GENERIC_REGISTRANT = re.compile(
    r"(?:\b[Tt]he\s+[\"'\u201c]?(?:[Cc]ompany|[Rr]egistrant)\b|\b[Rr]egistrant\b|"
    r"\b[Tt]he\s+[\"'\u201c]?(?:Corporation|Partnership|Trust|Fund)\b|\b[Ww]e\b)"
    r"(?!\s+(?:Parties|Entities|Group|Debtors?)\b)"
)
# Collective defined terms whose membership must be read from their definition.
_COLLECTIVE_TERM = re.compile(
    r"\b[Tt]he\s+((?:[A-Z][\w-]*\s+){0,2}(?:Debtors?|Entities|Parties))\b"
)
# "<name or term> ... and certain / one / each / all / substantially all of its
# subsidiaries" -- the registrant coordinated with its subsidiaries, allowing the
# `")` of a defined term in between (A3).
_REGISTRANT_COORDINATED = re.compile(
    r"^\s*(?:,?\s*\([^()]*\))?\s*,?\s*(?:and|or|together\s+with|along\s+with)\s+"
    r"(?:(?:certain|one|two|three|four|five|each|all|any|substantially|\d+)\s+)*"
    r"(?:of\s+)?(?:its|their|our)\b"
)
# The registrant as the OTHER end of a relationship, not as a filing party.
_POSSESSIVE = re.compile(r"^['’]s?(?=\W|$)")
# "<debtor>, a/an/the <up to six words> subsidiary of <parent>" (F). A comma must
# introduce it, so "the Company and its subsidiaries" is never an apposition.
_SUBSIDIARY_APPOSITIVE = re.compile(
    r",\s*(?:a|an|the)\s+(?!(?:company|registrant)\b)(?:[\w-]+\s+){0,6}?"
    r"subsidiar(?:y|ies)\s+of\b",
    re.IGNORECASE,
)
_SUBSIDIARY_WORD = re.compile(r"\b(?:subsidiar(?:y|ies)|affiliates?)\b", re.IGNORECASE)

_CLAUSE_FILING_VERB = re.compile(
    r"\b(?:(?:voluntarily|jointly)\s+)?(filed|commenced|initiated)\b", re.IGNORECASE
)
# A verb inside these frames is not an actual past filing.
_NOT_ACTUAL_FRAME = re.compile(
    r"(?:\b(?:to|will|would|shall|may|might|could|should|must|can)\s+(?:be\s+|have\s+been\s+)?|"
    r"\bbe\s+|\bbeing\s+|\bnot\s+(?:yet\s+)?(?:itself\s+|been\s+)?)$",
    re.IGNORECASE,
)
_CAUSED_TO_BE = re.compile(r"\bcaused\s+to\s+be\s+$", re.IGNORECASE)
_PASSIVE_FRAME = re.compile(r"\b(?:was|were|has\s+been|have\s+been|had\s+been)\s+$", re.IGNORECASE)
_HYPOTHETICAL_CLAUSE = re.compile(r"\b(?:if|unless|whether)\b|\bin\s+the\s+event\b", re.IGNORECASE)
# Clause openers: the subject of a filing verb starts after the last of these.
_CLAUSE_OPENER = re.compile(r";|\b(?:that|which|who|whereby|whereupon)\b")

_BANKRUPTCY_OBJECT = re.compile(
    r"\b(?:(?:voluntary|involuntary|bankruptcy|chapter\s*(?:7|11))\s+)*petitions?\b|"
    r"\b(?:voluntary|involuntary)\s+(?:(?:bankruptcy|chapter\s*(?:7|11))\s+)?(?:cases?|proceedings?)\b|"
    r"\bchapter\s*(?:7|11)\s+(?:bankruptcy\s+)?(?:cases?|proceedings?|bankruptcy|petitions?)\b|"
    r"\b(?:cases?|proceedings?)\s+under\s+(?:chapter\s*(?:7|11)|title\s+11)\b|"
    r"\bfor\s+(?:voluntary\s+)?(?:bankruptcy\s+)?(?:protection|reorganization|relief|liquidation)\b|"
    r"\bfor\s+(?:chapter\s*(?:7|11)|bankruptcy)\b|"
    r"\bbankruptcy\s+(?:cases?|proceedings?|protection)\b|"
    r"^\s*under\s+(?:the\s+provisions\s+of\s+)?chapter\s*(?:7|11)\b|"
    r"\bchapter\s*(?:7|11)\s+filings?\b",
    re.IGNORECASE,
)
_FILED_NON_PETITION = re.compile(
    r"\b(?:motions?|plans?|disclosure\s+statements?|adversary|complaints?|objections?|"
    r"applications?|notices?|schedules?|reports?|forms?|claims?|stipulations?|requests?|"
    r"amendments?|certificates?|registration|lawsuits?|suits?|actions?|appeals?|8-K)\b",
    re.IGNORECASE,
)
# A petition filed for a purpose other than starting a case (lower-case lexicon).
_PETITION_FOR_OTHER_PURPOSE = re.compile(
    r"\bto\s+(?:voluntarily\s+)?(?:dismiss|intervene|convert|vacate|reopen|appeal|compel|enforce)\b"
)
_BANKRUPTCY_CONTEXT = re.compile(
    r"\bchapter\s*(?:7|11)\b|\bbankruptcy\b|\btitle\s+11\b|\binvoluntary\b", re.IGNORECASE
)
_INVOLUNTARY_PETITION = re.compile(
    r"\binvoluntary\s+(?:(?:chapter\s*(?:7|11)|bankruptcy)\s+)*(?:petitions?|cases?|proceedings?)\b",
    re.IGNORECASE,
)
_AGAINST_OR_IN_RE = re.compile(r"\b(?:against|[Ii]n\s+re:?)\s+", re.IGNORECASE)
# "filed Chapter 11 petitions ... for three (3) of its wholly owned subsidiaries" (F).
_FILED_FOR_SUBSIDIARIES = re.compile(
    r"\b(?:for|on\s+behalf\s+of)\s+(?:(?:\w+|\(\d+\))\s+){0,3}(?:of\s+)?"
    r"(?:its|our|their|the\s+[Cc]ompany['’]s)\s+(?:[\w-]+\s+){0,3}subsidiar",
)
# Explicit negation (G), lower-case lexicon: "The Company itself has not filed
# for Bankruptcy protection", "is not a debtor".
_NEGATED_FILING = re.compile(
    r"\b(?:has|have|had|did|does|do)\s+not\s+(?:yet\s+)?(?:itself\s+)?(?:filed|commenced|sought)\b"
    r"|\b(?:is|are|was|were)\s+not\s+(?:a\s+|one\s+of\s+the\s+)?(?:debtors?|part(?:y|ies))\b"
    r"|\b(?:is|are|was|were)\s+not\s+(?:included|named)\s+(?:in|among)\b"
)
# Prospective intent, authorisation or preparation (G), lower-case lexicon.
_PROSPECTIVE_FILING = re.compile(
    r"\b(?:intends?|intended|plans?|planning|expects?|anticipates?|contemplates?|considering|"
    r"prepar(?:e|es|ed|ing)|authoriz(?:e|es|ed|ing)|approv(?:e|es|ed|ing)|vot(?:e|es|ed|ing)|"
    r"resolved|determined|decided|engage[sd]?)\b[^.;]{0,120}?"
    r"\b(?:to\s+(?:file|commence|seek|prepare)|on\s+(?:\w+\s+){0,4}filing|(?:the\s+)?filing\s+of)\b"
    r"|\bin\s+the\s+near\s+future\b|\bwill\s+(?:file|commence|seek)\b|\bbe\s+filed\b"
)
# Forward-looking and risk-factor sentences state no event (lower-case lexicon).
_RISK_SENTENCE = re.compile(
    r"\bforward-looking\b|\b(?:could|may|might)\s+cause\b|\brisks?\s+and\s+uncertainties\b"
    r"|\bfactors\s+(?:that\s+)?could\b"
)
# "motions filed in the Chapter 11 Cases": the case is where something else was filed.
_LOCATIVE_BEFORE_OBJECT = re.compile(
    r"\b(?:in|during|within|throughout|of)\s+(?:the\s+|its\s+|their\s+|our\s+|such\s+|these\s+)?$",
    re.IGNORECASE,
)
_CONSENTED_TO_RELIEF = re.compile(
    r"\bconsented\s+to\s+(?:the\s+entry\s+of\s+)?(?:an?\s+)?(?:[Oo]rder\s+for\s+)?"
    r"(?:bankruptcy\s+)?[Rr]elief\b"
)
_ADDITIONAL_REGISTRANTS = re.compile(r"\b(?:additional|co-?)\s*registrants?\b", re.IGNORECASE)


@dataclass
class _IdentityContext:
    """The registrant as the text can be matched to it, for one classify() call."""

    # (pattern, suffix class, is_former_name, needs_suffix) per EDGAR name.
    name_patterns: tuple[tuple[re.Pattern[str], str | None, bool, bool], ...] = ()
    co_registered: bool = False
    full_text: str = ""
    _aliases: tuple[re.Pattern[str], ...] | None = None
    _generic_defined: bool | None = None

    @property
    def generic_defined_as_registrant(self) -> bool:
        """The filing defines its generic term as this registrant by exact name:
        `Revlon, Inc. (the "Company")`. Only then does "the Company" name it in a
        co-registered filing."""
        if self._generic_defined is None:
            self._generic_defined = any(
                re.match(
                    r"[\s,.]*\(\s*(?:together\s+with\s+[^()]{0,60},\s*)?(?:the\s+)?[\"'“‘]?\s*"
                    r"(?:Company|Registrant|Partnership|Corporation|Trust)[\"'”’]?",
                    self.full_text[end: end + 60],
                )
                for pattern, suffix, _, needs_suffix in self.name_patterns
                for _, end in _name_matches(pattern, suffix, self.full_text, needs_suffix)
            )
        return self._generic_defined
    _collective: dict[str, tuple[bool, bool]] | None = None

    @property
    def aliases(self) -> tuple[re.Pattern[str], ...]:
        """Short names the filing defines: `eMerge Interactive, Inc. ("eMerge")`."""
        if self._aliases is None:
            found = []
            for pattern, suffix, _, needs_suffix in self.name_patterns:
                for _, match_end in _name_matches(pattern, suffix, self.full_text, needs_suffix):
                    tail = self.full_text[match_end: match_end + 60]
                    defined = re.match(
                        rf"[\s,.]*(?:{_ENTITY_SUFFIX_WORD}\.?[\s,]*)*\(\s*(?:the\s+)?"
                        r"[\"'“‘]([A-Za-z][\w&.-]{1,30}(?:\s[\w&.-]+){0,2})[\"'”’]",
                        tail,
                    )
                    if defined and not _GENERIC_REGISTRANT.fullmatch("the " + defined.group(1)) \
                            and not _COLLECTIVE_TERM.fullmatch("the " + defined.group(1)):
                        found.append(re.compile(
                            rf"(?<![\w-]){re.escape(defined.group(1))}(?![\w-])"
                            rf"(?![\s,-]{{1,3}}(?!{_ENTITY_SUFFIX_WORD}\b)[A-Z][A-Za-z]+)"
                        ))
            self._aliases = tuple(found)
        return self._aliases


def _name_pattern(name: str) -> tuple[re.Pattern[str], str | None, bool] | None:
    """A registrant name as a regex tolerant of punctuation, plus its suffix class.

    A sibling that merely extends the name ("Refco" vs "Refco Group") is refused:
    the match may not run on into another capitalised name word. The suffix is
    captured so a different entity type ("... Inc" for a "... Corp") is refused
    by `_name_matches`. An apostrophe after the first letter is optional, since
    EDGAR writes "OSULLIVAN" for "O'Sullivan".
    """
    name = re.sub(r"\s*/[A-Za-z]{2,4}/?\s*$", "", name)
    tokens = re.findall(r"[A-Za-z0-9]+", name)
    suffix = None
    while tokens and tokens[-1].lower() in _NAME_SUFFIX_TOKENS:
        suffix = _SUFFIX_CLASS.get(tokens.pop().lower(), suffix)
    while tokens and tokens[0].lower() == "the":
        tokens.pop(0)
    if not tokens:
        return None
    # A short one-word name ("DRI") only counts with its entity suffix ("DRI Corporation").
    needs_suffix = len(tokens) == 1 and len(tokens[0]) < 4
    body = r"(?:\s+(?:and|&)\s+|[\W_]{0,3})".join(map(_name_token_pattern, tokens))
    return re.compile(
        rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])"
        rf"(?![\s,-]{{1,3}}(?-i:(?!{_ENTITY_SUFFIX_WORD}\b)[A-Z][A-Za-z]+))",
        re.IGNORECASE,
    ), suffix, needs_suffix


_TOKEN_EQUIVALENTS = {
    "co": "(?:co|company)", "company": "(?:co|company)", "corp": "(?:corp|corporation)",
    "corporation": "(?:corp|corporation)", "inc": "(?:inc|incorporated)",
    "intl": "(?:intl|international)", "international": "(?:intl|international)",
}


def _name_token_pattern(token: str) -> str:
    """One name word: EDGAR abbreviations are equivalent to their long forms."""
    if token.lower() in _TOKEN_EQUIVALENTS:
        return _TOKEN_EQUIVALENTS[token.lower()]
    if len(token) <= 3 and token.isalpha():
        # EDGAR's "US" is the text's "U.S.".
        return r"\.?".join(map(re.escape, token)) + r"\.?"
    return re.escape(token[0]) + r"['\u2019]?" + re.escape(token[1:])


_FOLLOWING_SUFFIX = re.compile(rf"[\s,]{{1,3}}({_ENTITY_SUFFIX_WORD})\b\.?", re.IGNORECASE)


def _name_matches(pattern: re.Pattern[str], suffix: str | None, text: str,
                  needs_suffix: bool = False) -> list[tuple[int, int]]:
    """(start, end) of each match, the end extended over a following entity suffix.

    Extending the end keeps a possessive adjacent ("EchoStar Corporation's
    subsidiary"); a suffix of a different class is a different entity.
    """
    spans = []
    for match in pattern.finditer(text):
        end = match.end()
        following = _FOLLOWING_SUFFIX.match(text, end)
        if following:
            if suffix and _SUFFIX_CLASS.get(following.group(1).lower()) != suffix:
                continue
            end = following.end()
        elif needs_suffix:
            continue
        spans.append((match.start(), end))
    return spans


def _depth0_positions(text: str, pattern: re.Pattern[str]) -> list[re.Match[str]]:
    depth, depths = 0, []
    for char in text:
        depths.append(depth)
        depth += char == "("
        depth -= char == ")" and depth > 0
    return [m for m in pattern.finditer(text) if depths[m.start()] == 0]


def _registrant_refs(span: str, ctx: _IdentityContext,
                     with_collective: bool = True) -> list[tuple[int, int, str]]:
    """(start, end, kind) of every reference that may denote the registrant."""
    refs = [(m.start(), m.end(), "generic") for m in _GENERIC_REGISTRANT.finditer(span)]
    for pattern, suffix, _, needs_suffix in ctx.name_patterns:
        refs += [
            (start, end, "name")
            for start, end in _name_matches(pattern, suffix, span, needs_suffix)
        ]
    if ctx.generic_defined_as_registrant:
        # "the Company" is this registrant's defined term, so it names it; "we" does not.
        refs = [
            (start, end, "name" if kind == "generic" and span[start:end].lower() != "we" else kind)
            for start, end, kind in refs
        ]
    for pattern in ctx.aliases:
        refs += [(m.start(), m.end(), "name") for m in pattern.finditer(span)]
    if with_collective:
        for match in _COLLECTIVE_TERM.finditer(span):
            includes, named = _collective_includes_registrant(match.group(1), ctx)
            if includes:
                kind = "collective_named" if named else "collective"
                refs.append((match.start(), match.end(), kind))
    return sorted(refs)


def _is_parent_reference(span: str, start: int, end: int) -> bool:
    """Is this reference the parent/relationship end, not a party in its own right?"""
    if _POSSESSIVE.match(span[end: end + 3]) and _SUBSIDIARY_WORD.search(span[end: end + 60]):
        return True
    # A defined term inside the parent's parenthetical inherits its role:
    # `EchoStar Corporation's ("EchoStar") subsidiary Hughes ...`.
    opening = span.rfind("(", 0, start)
    if opening != -1 and span.find(")", opening) >= end:
        if re.search(r"['\u2019]s?\s*$", span[:opening]) and _SUBSIDIARY_WORD.search(
            span[end: end + 60]
        ):
            return True
    before = span[max(0, start - 160): start]
    # "<relation> of <name> (the Company)" -- the reference follows the relation
    # directly or after the parent's name, with no coordination in between.
    # Also the child end of "the indirect parent of <registrant>" and the issuer end
    # of "the sole owner of the common securities of <registrant>".
    window = re.search(
        r"\b(?:subsidiar(?:y|ies)|affiliates?|(?:managing\s+)?general\s+partner|member|division|"
        r"parent(?:\s+company)?|owner|holder|sponsor|guarantor|manager)"
        r"\s+of\b(?P<gap>[^;]*)$",
        before,
    )
    if window is None:
        return False
    gap = re.sub(r"\([^()]*$", "", re.sub(r"\([^()]*\)", "", window.group("gap")))
    # "subsidiaries of the Trust and the Operating Partnership" names two parents;
    # only a comma-led coordination starts a new party ("..., and the Company").
    if re.search(r",\s*(?:and|together\s+with|along\s+with)\b|\bas\s+well\s+as\b", gap):
        return False
    # A generic reference placed straight after a list comma starts the next list
    # item: "the direct parent of the Company, the Company and certain of ...". Names
    # in "the indirect parent company of A, B, C and D" stay relation objects, as do
    # references after a descriptor ("SARS Corporation, a Nevada Company (SARS)") or
    # an entity suffix (", Inc. (the Company)").
    generic = _GENERIC_REGISTRANT.fullmatch(span[start:end]) is not None
    return not (generic and re.search(r"[A-Za-z][^,]*,\s*$", gap))


def _collective_includes_registrant(term: str, ctx: _IdentityContext) -> tuple[bool, bool]:
    """Does the definition of "the Debtors" (or similar) include the registrant?

    Returns (includes, named): named when an exact name, not a generic term, did it.
    Only a definition in the same primary filing counts; with none, membership is
    unknown and the answer is no -- unresolved identity is never positive.
    """
    if ctx._collective is None:
        ctx._collective = {}
    if term in ctx._collective:
        return ctx._collective[term]
    includes = named = False
    definition = re.compile(
        r"\(([^()]{0,240}?)[\"'“‘]\s*" + re.escape(term) + r"\s*[,.]?[\"'”’]"
    )
    text = ctx.full_text
    for match in definition.finditer(text):
        sentence_start = max(text.rfind(". ", 0, match.start()), match.start() - 900, 0)
        prefix = text[sentence_start: match.start()]
        inside = match.group(1)
        for span in (inside, prefix):
            refs = _registrant_refs(span, ctx, with_collective=False)
            live = [r for r in refs if not _is_parent_reference(span, r[0], r[1])]
            if span is prefix:
                # Only the list that the parenthetical closes: drop an earlier,
                # unrelated clause ending in "; " or a completed sentence.
                live = [r for r in live if not re.search(r";", prefix[r[1]:])]
            if live:
                includes = True
                named = named or any(kind == "name" for _, _, kind in live)
        if span_mentions_additional_registrants(inside + prefix):
            includes = includes or _registrant_named_anywhere(ctx)
            named = named or _registrant_named_anywhere(ctx)
        if includes:
            break
    ctx._collective[term] = (includes, named)
    return includes, named


def span_mentions_additional_registrants(span: str) -> bool:
    return bool(_ADDITIONAL_REGISTRANTS.search(span))


def _registrant_named_anywhere(ctx: _IdentityContext) -> bool:
    return any(
        _name_matches(pattern, suffix, ctx.full_text, needs_suffix)
        for pattern, suffix, _, needs_suffix in ctx.name_patterns
    )


@dataclass(frozen=True)
class _FilingClause:
    registrant: bool          # the registrant is a filing party
    named: bool               # ... through an exact name (or its defined alias)
    subsidiary: bool          # subsidiaries/affiliates are parties
    apposition: bool          # a "<debtor>, a subsidiary of <registrant>" subject
    additional_registrants: bool
    involuntary: bool


def _subject_span(sentence: str, verb_start: int) -> str:
    """The text before a verb that can hold its subject.

    Starts after the last clause opener, ignoring a non-restrictive aside
    (", which is incorporated herein by reference,") and a semicolon that only
    separates list items ("its wholly owned subsidiaries; GameTech Arizona Corp").
    """
    head = sentence[max(0, verb_start - 900): verb_start]
    for opener in reversed(_depth0_positions(head, _CLAUSE_OPENER)):
        if opener.group(0) != ";" and re.search(r",\s*$", head[: opener.start()]) \
                and re.search(r",\s*$", head):
            continue
        if opener.group(0) == ";" and not _FINITE_VERB.search(head[: opener.start()]):
            continue
        return head[opener.end():]
    return head


def _parties(span: str, ctx: _IdentityContext) -> tuple[bool, bool, bool, bool]:
    """(registrant, named, subsidiary, apposition) for one party span."""
    refs = _registrant_refs(span, ctx)
    live = [r for r in refs if not _is_parent_reference(span, r[0], r[1])]
    apposition = bool(_SUBSIDIARY_APPOSITIVE.search(span))
    if apposition:
        # "<debtor>, a subsidiary of <parent>": references after the apposition
        # opener belong to the parent unless coordinated back into the subject.
        opener = _SUBSIDIARY_APPOSITIVE.search(span)
        live = [r for r in live if r[1] <= opener.start()
                or _REGISTRANT_COORDINATED.match(span[r[1]:])]
    return (
        bool(live),
        any(kind in ("name", "collective_named") for _, _, kind in live),
        bool(_SUBSIDIARY_WORD.search(span)),
        apposition,
    )


def _filing_clauses(sentence: str, ctx: _IdentityContext) -> list[_FilingClause]:
    """Every actual, past bankruptcy filing stated in one sentence, with its parties."""
    if not _BANKRUPTCY_CONTEXT.search(sentence) or _RISK_SENTENCE.search(sentence):
        return []
    clauses = []
    for verb in _CLAUSE_FILING_VERB.finditer(sentence):
        before = sentence[max(0, verb.start() - 40): verb.start()]
        if _NOT_ACTUAL_FRAME.search(before) and not _CAUSED_TO_BE.search(before):
            continue
        # "motions filed in ...", "the Plan filed by ...": a reduced relative on
        # some other document, not a petition filing.
        if re.search(r"\b(?:motions?|plans?|pleadings?|objections?|documents?|claims?|"
                     r"reports?|statements?|notices?|applications?)\s+$", before, re.IGNORECASE):
            continue
        after = _PARENTHETICAL_SPAN.sub(" ", sentence[verb.end(): verb.end() + 400])[:260]
        target = _AGAINST_OR_IN_RE.match(after.lstrip()) if after.lstrip() else None
        preceding_object = _BANKRUPTCY_OBJECT.search(
            _PARENTHETICAL_SPAN.sub(" ", sentence[max(0, verb.start() - 60): verb.start()])
        )
        petition = next((m for m in _BANKRUPTCY_OBJECT.finditer(after)
                         if not _LOCATIVE_BEFORE_OBJECT.search(after[: m.start()])), None)
        other = _FILED_NON_PETITION.search(after)
        passive = bool(_PASSIVE_FRAME.search(before)) or (
            preceding_object is not None and petition is None
        )
        if not passive:
            if petition is None or (other is not None and other.start() < petition.start()):
                continue
            if _PETITION_FOR_OTHER_PURPOSE.search(after[petition.start(): petition.end() + 120]):
                continue
            subject = _subject_span(sentence, verb.start())
            if _HYPOTHETICAL_CLAUSE.search(subject) or _NEITHER_NONE.search(subject):
                continue
            registrant, named, subsidiary, apposition = _parties(subject, ctx)
            if not registrant and _PRONOUN_SUBJECT.match(subject):
                main = sentence[max(0, verb.start() - 900): verb.start() - len(subject)]
                registrant, named, _, _ = _parties(main, ctx)
            if _FILED_FOR_SUBSIDIARIES.search(after[: petition.end() + 160]) and not re.search(
                r"\bitself\b|\b[Tt]he\s+[Cc]ompany\s+and\b", after[: petition.end() + 160]
            ):
                registrant, named, subsidiary = False, False, True
            clauses.append(_FilingClause(registrant, named, subsidiary, apposition,
                                         span_mentions_additional_registrants(subject), False))
        elif target is not None or re.match(r"\s*by\s+", after):
            party = re.split(r"\bby\b", after, maxsplit=1)[-1] if target is None else \
                after.lstrip()[target.end():]
            party = re.split(
                r"(?<!Inc),\s+(?:filed|in|by|on|an|the\s+United)\b|\s+filed\b", party
            )[0][:160]
            registrant, named, subsidiary, apposition = _parties(party, ctx)
            clauses.append(_FilingClause(registrant, named, subsidiary, apposition, False,
                                         target is not None))
    # "Following the filing of an involuntary petition ..., Impart Media Group, Inc.
    # (the "Company") consented to bankruptcy relief": the consenting party is the
    # involuntary debtor.
    order_for_relief = re.search(r"\border\s+for\s+relief\b", sentence, re.IGNORECASE)
    if _INVOLUNTARY_PETITION.search(sentence) or order_for_relief:
        for consent in _CONSENTED_TO_RELIEF.finditer(sentence):
            registrant, named, subsidiary, apposition = _parties(
                _subject_span(sentence, consent.start()), ctx
            )
            clauses.append(_FilingClause(registrant, named, subsidiary, apposition, False, True))
    # "involuntary petition ... against <party>" with the verb elsewhere or absent
    # ("the previously reported involuntary petition under Chapter 7 against
    # MidgardXXI, Inc.", "an involuntary petition ... styled In re: Vesta ...").
    for petition in _INVOLUNTARY_PETITION.finditer(sentence):
        if _NOT_ACTUAL_FRAME.search(sentence[max(0, petition.start() - 40): petition.start()]):
            continue
        tail = sentence[petition.end(): petition.end() + 260]
        target = _AGAINST_OR_IN_RE.search(tail)
        if target is None:
            continue
        party = re.split(
            r"\s+(?:filed|by|in\s+the\s+United)\b|,\s+Case\b|;", tail[target.end():]
        )[0][:160]
        registrant, named, subsidiary, apposition = _parties(party, ctx)
        clauses.append(_FilingClause(registrant, named, subsidiary, apposition, False, True))
    return clauses


_PARENTHETICAL_SPAN = re.compile(r"\([^()]*\)")
# "Neither the Company nor any other subsidiary ... has filed": a negated subject.
_NEITHER_NONE = re.compile(r"\b(?:[Nn]either|[Nn]one\s+of)\b")
_FINITE_VERB = re.compile(r"\b(?:filed|commenced|entered|is|are|was|were|has|have|had|announced)\b")
# "it" as the subject of a reported filing: "X (the Company) announced that it had filed".
_PRONOUN_SUBJECT = re.compile(
    r"^[\s,]*(?:on\s+(?:or\s+about\s+)?[A-Za-z]+\.?\s+\d{1,2},?\s+\d{4},?\s*)?it\b(?!['’])"
)
# Nouns that make a possessive registrant the owner of something else: "the
# Company's operating entities ... are not party".
_OWNED_NOUN = re.compile(
    r"\b(?:subsidiar(?:y|ies)|affiliates?|entit(?:y|ies)|operations|businesses|units?|divisions?)\b",
    re.IGNORECASE,
)


def _registrant_negated(sentence: str, ctx: _IdentityContext) -> bool:
    """An explicit statement that the registrant itself did not file / is not a debtor."""
    if not _BANKRUPTCY_CONTEXT.search(sentence) and "protection" not in sentence.lower():
        return False
    for verb in _CLAUSE_FILING_VERB.finditer(sentence):
        subject = _subject_span(sentence, verb.start())
        neither = _NEITHER_NONE.search(subject)
        if neither:
            stop = re.search(r"\b(?:nor|besides|other\s+than|except)\b", subject[neither.end():])
            head_end = neither.end() + stop.start() if stop else len(subject)
            if any(
                neither.end() <= a < head_end and not _is_parent_reference(subject, a, b)
                and not _OWNED_NOUN.search(subject[b:head_end])
                for a, b, _ in _registrant_refs(subject, ctx)
            ):
                return True
    for negation in _NEGATED_FILING.finditer(sentence):
        # "has not filed its annual report" negates a report, not a petition.
        if re.search(r"\b(?:filed|commenced|sought)$", negation.group(0)):
            obj = _PARENTHETICAL_SPAN.sub(" ", sentence[negation.end(): negation.end() + 120])
            petition = _BANKRUPTCY_OBJECT.search(obj)
            other = _FILED_NON_PETITION.search(obj)
            if petition is None or (other is not None and other.start() < petition.start()):
                continue
        subject = _subject_span(sentence, negation.start())
        for start, end, _ in _registrant_refs(subject, ctx):
            # The negated party is the nearest subject; relationship context is read
            # from the whole span ("subsidiaries of the Trust and the Operating
            # Partnership ... are not included").
            if len(subject) - start > 160:
                continue
            if _is_parent_reference(subject, start, end) or _OWNED_NOUN.search(subject[end:]):
                continue
            return True
    return False


def _registrant_is_debtor_in(sentence: str, ctx: _IdentityContext | None = None) -> bool:
    """The registrant is a filing party in an actual filing clause of this sentence."""
    ctx = ctx or _IdentityContext(full_text=sentence)
    return any(clause.registrant for clause in _filing_clauses(sentence, ctx))


# Single letters are initials ("J. Gordon Gaines", "S. de R.L."), but not the
# form letter of "Form 10-K." ending a sentence.
_IDENTITY_ABBREVIATION = re.compile(
    r"(?<![-\d])\b(No|Nos|Mr|Ms|Mrs|Dr|St|Mt|Jr|Sr|vs|v|al|et|U\.S|U\.S\.A|seq|[A-Za-z])\."
)
# Normalisation drops the full stop of "Inc." even where it ended a sentence --
# "... Crescent Oil Company, Inc Also on February 9, 2009, Appalachian Oil ..." --
# and masking "U.S." hides a sentence that really ends there ("in the U.S. Its
# subsidiary filed").
_SUFFIX_SENTENCE_RESTART = re.compile(
    r"\b(Inc|Corp|Ltd|LLC|LP|Co|plc|U\.S\.)\s+(?=(?:Also|On|In|The|As|Additionally|Further|"
    r"Thereafter|Subsequently|Such|This|These|Pursuant|Its|Our|We)\s)"
)


def _identity_sentences(text: str) -> list[str]:
    """Sentences for identity rules: also split after a closing quote or bracket
    (`... et al.” Certain of ...`) and where a dropped full stop is evident."""
    return [
        part
        for sentence in _split_sentences(text, _IDENTITY_ABBREVIATION)
        for piece in re.split(r"(?<=[.!?][\"\u201d\u2019)])\s+(?=[A-Z])", sentence)
        for part in _SUFFIX_SENTENCE_RESTART.sub("\\1\x01", piece).split("\x01")
    ]


def _strong_filing_sentences(text: str, ctx: _IdentityContext) -> list[str]:
    """Sentences carrying an actual registrant filing clause and a Chapter 7/11 reference."""
    return [
        sentence for sentence in _identity_sentences(text)
        if (CHAPTER_7.search(sentence) or CHAPTER_11.search(sentence))
        and _registrant_is_debtor_in(sentence, ctx)
    ]


def _classify_text(
    document_text: str, full_text: str | None = None, ctx: _IdentityContext | None = None
) -> Classification:
    """Disposition rules applied to already-located, normalised text.

    `full_text` is the whole normalised primary filing, consulted to resolve a
    "Petition Date" or a collective term ("the Debtors") the section uses but
    defines elsewhere.
    """
    ctx = ctx or _IdentityContext(full_text=" ".join((full_text or document_text).split()))
    matched: list[str] = []

    has_chapter_7 = bool(CHAPTER_7.search(document_text))
    has_chapter_11 = bool(CHAPTER_11.search(document_text))
    sentences = _identity_sentences(document_text)
    clauses = [clause for sentence in sentences for clause in _filing_clauses(sentence, ctx)]
    registrant_clauses = [c for c in clauses if c.registrant]
    negated = any(_registrant_negated(sentence, ctx) for sentence in sentences)
    prospective = any(_PROSPECTIVE_FILING.search(sentence) for sentence in sentences)

    for name, hit in (
        ("chapter_7", has_chapter_7),
        ("chapter_11", has_chapter_11),
        ("registrant_filing_clause", bool(registrant_clauses)),
        ("involuntary_against_registrant", any(c.involuntary for c in registrant_clauses)),
        ("subsidiary_filing_clause", any(c.subsidiary and not c.registrant for c in clauses)),
        ("subsidiary_apposition", any(c.apposition and not c.registrant for c in clauses)),
        ("registrant_negated", negated),
    ):
        if hit:
            matched.append(name)

    petition_date, date_rule = _rank_petition_date(document_text, full_text, ctx)
    if date_rule:
        matched.append(date_rule)
    court = _first_group(COURT, document_text)
    docket = _first_group(DOCKET, document_text)

    def result(disposition: Disposition, *extra: str, chapter: int | None = None,
               converted: bool = False) -> Classification:
        return Classification(disposition, petition_date, court, docket,
                              tuple(matched) + extra, chapter=chapter,
                              converted_to_chapter_7=converted)

    if not has_chapter_7 and not has_chapter_11:
        if RECEIVERSHIP.search(document_text):
            return result(Disposition.RECEIVERSHIP_ONLY, "receivership")
        return result(Disposition.AMBIGUOUS)

    # G: an explicit statement that the registrant did not file overrides every
    # positive cue. The subsidiaries' own filing, if stated, is what remains.
    if negated:
        if any(c.subsidiary and not c.registrant for c in clauses):
            return result(Disposition.SUBSIDIARY_ONLY)
        return result(Disposition.AMBIGUOUS)

    if registrant_clauses:
        if ctx.co_registered and ctx.name_patterns:
            # LABEL_POLICY 11: in a filing made under several CIKs, "the Company"
            # may be another registrant. Positive only if THIS registrant is named
            # among the filing parties or in their definition, or the debtor
            # definition includes the "additional registrants" and this
            # registrant's exact name is listed in the filing.
            if any(c.named for c in registrant_clauses):
                matched.append("coregistrant_named")
            elif any(c.additional_registrants for c in clauses) and _registrant_named_anywhere(ctx):
                matched.append("coregistrant_additional_registrants")
            else:
                return result(Disposition.AMBIGUOUS, "coregistrant_unconfirmed")
        chapter, converted = _initial_chapter(document_text, ctx)
        # The benchmark chapter is the chapter of the INITIAL petition (LABEL_POLICY
        # 1, 5, 6), never a DIP default trigger, risk boilerplate, a subsidiary's
        # own Chapter 7 or an unapproved conversion motion.
        if chapter is None:
            return result(Disposition.AMBIGUOUS, "chapter_hypothetical_only", converted=converted)
        disposition = (
            Disposition.REGISTRANT_CHAPTER_7 if chapter == 7 else Disposition.REGISTRANT_CHAPTER_11
        )
        return result(disposition, chapter=chapter, converted=converted)

    # F: "<debtor>, a/the ... subsidiary of <registrant>" is two-sided -- rules
    # cannot parse which entity the apposition's head is -- so it is AMBIGUOUS,
    # never positive and never confidently subsidiary-only.
    if any(c.apposition for c in clauses):
        return result(Disposition.AMBIGUOUS)
    if any(c.subsidiary for c in clauses):
        # In a filing made under several CIKs, "certain of its subsidiaries" may
        # include this registrant: unresolved, not subsidiary-only (LABEL_POLICY 11).
        if ctx.co_registered and ctx.name_patterns:
            return result(Disposition.AMBIGUOUS, "coregistrant_unconfirmed")
        return result(Disposition.SUBSIDIARY_ONLY)
    if prospective:
        return result(Disposition.AMBIGUOUS, "prospective_only")

    # No actual filing clause at all (a confirmation order, a plan filing, a
    # status update). Subsidiary-only stays available when the text scopes the
    # bankruptcy to subsidiaries and never coordinates the registrant with them;
    # a registrant coordinated with its subsidiaries is unresolved, not dropped.
    if SUBSIDIARY_SCOPED.search(document_text) and not _registrant_coordinated(document_text, ctx):
        return result(Disposition.SUBSIDIARY_ONLY, "subsidiary_scoped_no_clause")
    return result(Disposition.AMBIGUOUS)


def _registrant_coordinated(text: str, ctx: _IdentityContext) -> bool:
    return any(
        _REGISTRANT_COORDINATED.match(text[end:])
        for _, end, _ in _registrant_refs(text, ctx)
    )


# The filer's own definition: "On April 16, 2026 (the "Petition Date"), ...".
_PETITION_DATE_LABEL = re.compile(
    r"^\s*\(\s*(?:the\s+)?[\"'“”‘’]?\s*Petition\s+Date\b", re.IGNORECASE
)
_PETITION_DATE_TERM = re.compile(r"\bPetition\s+Date\b")
# Verbs that can carry the petition. Broader than _FILING_VERB ("is commencing a
# bankruptcy case ... by filing a voluntary petition"), but only ever accepted
# with a petition object as the thing filed.
_DATE_FILING_VERB = re.compile(
    r"\b(?:filed|files|filing|commenced|commences|commencing|initiated)\b", re.IGNORECASE
)
# Things filed in a bankruptcy that are not the petition.
_NON_PETITION_OBJECT = re.compile(
    r"\b(?:motions?|plans?|disclosure\s+statements?|adversary|complaints?|objections?|"
    r"applications?|notices?|schedules?|reports?|forms?|claims?|stipulations?|requests?|"
    r"amendments?|certificates?|registration|8-K)\b",
    re.IGNORECASE,
)
# Words that tie a date to some other event: an order, a hearing, a vote, a
# dismissal or conversion, a report or press release.
_OTHER_EVENT = re.compile(
    r"\b(?:orders?|entered|grant\w*|confirm\w*|hearings?|motions?|dismiss\w*|"
    r"conver(?:t|ts|ted|ting|sion)|vot(?:e|es|ed|ing)|authoriz\w*|prepar\w*|approv\w*|"
    r"announc\w*|issued|received|appoint\w*|closed|press\s+release|reports?|8-K)\b",
    re.IGNORECASE,
)
_TRAILING_OTHER_EVENT = re.compile(
    _OTHER_EVENT.pattern + r"|\b(?:SEC|Securities\s+and\s+Exchange\s+Commission)\b",
    re.IGNORECASE,
)
_PARENTHETICAL = re.compile(r"\([^()]*\)")
_COORDINATED_DATE = re.compile(
    r"\b(?:subsequently|thereafter|later)\b[^.;]{0,15}\bon(?:\s+or\s+about)?\s*$", re.IGNORECASE
)
# The date closes a clause of its own filing verb: "Form 8-K filed on <date>, the
# Company filed ..." dates the report, not the petition.
_PRECEDING_FILING_VERB = re.compile(
    r"\b(?:filed|furnished)\b(?:(?!\bthat\b)[^.;,]){0,60}\bon(?:\s+or\s+about)?\s*$",
    re.IGNORECASE,
)
# Nouns that can be the passive subject of "was filed/commenced on <date>".
_PASSIVE_PETITION_SUBJECT = re.compile(r"\b(?:petitions?|cases?|proceedings?)\b", re.IGNORECASE)
# "an amended Chapter 11 plan", "the Chapter 7 trustee": the chapter qualifies another noun.
_CHAPTER_QUALIFIES_OTHER = re.compile(
    r"^\s+(?:bankruptcy\s+)?(?:plans?|trustees?|motions?|disclosure|reports?|claims?)\b",
    re.IGNORECASE,
)
_CHAPTER_15 = re.compile(r"\bchapter\s*15\b", re.IGNORECASE)
# A petition filed for some purpose other than commencing a case.
_PETITION_PURPOSE_REJECT = re.compile(r"\b(?:dismiss|conver)", re.IGNORECASE)
_LEADING_PREPOSITION = re.compile(
    r"(?:\b(?:on|effective)(?:\s+or\s+about)?\s*|^[\W\d]*)$", re.IGNORECASE
)
_TRAILING_PREPOSITION = re.compile(r"\b(?:on(?:\s+or\s+about)?|was)\s*$", re.IGNORECASE)
# A leading date can sit before a long list of jointly filing debtors
# (Barnett Shale names eleven affiliates between the date and "filed").
_MAX_LEADING_CHARS = 1000
_MAX_TRAILING_CHARS = 400


def _parse_date_mention(match: re.Match[str]) -> date | None:
    month = match.group("m1") or match.group("m2")
    day = match.group("d1") or match.group("d2")
    year = match.group("y1") or match.group("y2")
    try:
        return date(int(year), MONTHS_BY_PREFIX[month[:3].lower()], int(day))
    except (KeyError, ValueError):
        return None


def _date_attaches_to_petition(
    sentence: str, match: re.Match[str], others: list[re.Match[str]]
) -> bool:
    """Is this date the date ON WHICH a petition was filed, in this sentence?

    Leading shape: "On <date>, <subject> filed <petition>" -- the nearest filing
    verb after the date governs it, nothing between may name another event, and
    the first thing filed must be a petition/case/protection, not a motion, plan,
    request or adversary proceeding, nor a petition "to dismiss" or "to convert".

    Trailing shape: "<petition> ... filed ... on <date>" -- the nearest filing
    verb before the date governs it, the object nearest the date is a petition
    ("filed a Plan ... with its Chapter 11 petition on"), and nothing between
    names another event or the SEC.

    Another date between the date and its verb breaks the attachment -- in "the
    Form 8-K filed on April 17, 2026, on April 16, 2026 (the Petition Date) ...
    filed voluntary petitions" only April 16 governs the petition -- unless that
    date is parenthetical: "on April 1, 2009 (and April 2, 2009 with respect to
    CAPA), the Company ... filed".
    """
    others = [other for other in others if other is not match]
    return _attaches_leading(sentence, match, others) or _attaches_trailing(
        sentence, match, others
    )


def _blocked_by_date(sentence: str, span_start: int, span_end: int,
                     others: list[re.Match[str]]) -> bool:
    """Does another date sit between a date and its verb?

    Parenthetical dates and coordinated dates for other debtors do not block:
    "on November 18, 2024, Spirit Airlines Inc (the Company), and subsequently
    on November 25, 2024, its subsidiaries ... filed" dates the registrant's
    petition November 18.
    """
    for other in others:
        if span_start <= other.start() < span_end:
            prefix = sentence[span_start: other.start()]
            if prefix.count("(") > prefix.count(")"):
                continue
            window = sentence[max(span_start, other.start() - 40): other.start()]
            if _COORDINATED_DATE.search(window):
                continue
            return True
    return False


def _attaches_leading(sentence: str, match: re.Match[str], others: list[re.Match[str]]) -> bool:
    start, end = match.start(), match.end()
    lead = sentence[max(0, start - 24): start]
    if not (_LEADING_PREPOSITION.search(lead) or not sentence[:start].strip()):
        return False
    if _PRECEDING_FILING_VERB.search(sentence[max(0, start - 80): start]):
        return False
    # Capitalised "Filing" is a label or heading ("(the Filing Date)"), not the verb.
    verb = next((v for v in _DATE_FILING_VERB.finditer(sentence, end) if v.group(0)[0].islower()),
                None)
    if verb is None or verb.start() - end > _MAX_LEADING_CHARS:
        return False
    if _blocked_by_date(sentence, end, verb.start(), others):
        return False
    # Parentheticals are defined terms and former names ("T3 Motion, Inc"), not events.
    if _OTHER_EVENT.search(_PARENTHETICAL.sub(" ", sentence[end: verb.start()])):
        return False
    after = sentence[verb.end(): verb.end() + 200]
    petition = _PETITION_OBJECT.search(after)
    other = _NON_PETITION_OBJECT.search(after)
    if petition is None or (other is not None and other.start() < petition.start()):
        return False
    if _CHAPTER_QUALIFIES_OTHER.match(after[petition.end():]):
        return False
    return not _PETITION_PURPOSE_REJECT.search(after[: petition.end() + 100])


def _attaches_trailing(sentence: str, match: re.Match[str], others: list[re.Match[str]]) -> bool:
    start = match.start()
    preposition = _TRAILING_PREPOSITION.search(sentence[max(0, start - 24): start])
    # A capitalised "On" opens a new clause, and a capitalised "Filing" is a
    # heading ("Voluntary Filing Under Chapter 11 On March 31, 2024, ...").
    if preposition is None or preposition.group(0)[0].isupper():
        return False
    verbs = [verb for verb in _DATE_FILING_VERB.finditer(sentence, 0, start)
             if start - verb.end() <= _MAX_TRAILING_CHARS and verb.group(0)[0].islower()]
    if not verbs:
        return False
    verb = verbs[-1]
    between = sentence[verb.end(): start]
    if _blocked_by_date(sentence, verb.end(), start, others):
        return False
    if _TRAILING_OTHER_EVENT.search(between):
        return False
    passive_start = max(0, verb.start() - 100)
    objects = [(m.start(), True)
               for m in _PASSIVE_PETITION_SUBJECT.finditer(sentence, passive_start, verb.start())]
    objects += [(m.start(), True) for m in _PETITION_OBJECT.finditer(sentence, verb.end(), start)
                if not _CHAPTER_QUALIFIES_OTHER.match(sentence[m.end():])]
    objects += [(m.start(), False)
                for m in _NON_PETITION_OBJECT.finditer(sentence, passive_start, start)]
    return bool(objects) and max(objects)[1]


def _labelled_petition_dates(text: str) -> list[tuple[date, bool]]:
    """Dates the filer defines as "the Petition Date", with a compound flag."""
    found = []
    for match in DATE_MENTION.finditer(text):
        if _PETITION_DATE_LABEL.match(text[match.end(): match.end() + 40]):
            parsed = _parse_date_mention(match)
            if parsed is not None:
                found.append((parsed, bool(match.group("second"))))
    return found


def _is_date_petition_sentence(sentence: str) -> bool:
    # A Chapter 15 petition seeks recognition of a foreign proceeding (LABEL_POLICY 3).
    if _CHAPTER_15.search(sentence) and not _CHAPTER.search(sentence):
        return False
    return bool(
        (_DATE_FILING_VERB.search(sentence) and _PETITION_OBJECT.search(sentence))
        or _INVOLUNTARY_OR_RELIEF.search(sentence)
    )


def _rank_petition_date(
    section_text: str, full_text: str | None = None, ctx: _IdentityContext | None = None
) -> tuple[date | None, str | None]:
    """The petition date and how it was established, or (None, None).

    Dates are ranked by their relationship to the bankruptcy filing, never by
    position in the section. In order:

      1. a date the section defines as "the Petition Date"
      2. a date attached to the petition in a sentence where the registrant
         is a filing party
      3. a date attached to the petition in any other petition sentence
      4. the section refers to "the Petition Date" and the primary filing
         defines it elsewhere (Avaya, Lilis: the definition sits in Item 1.01)

    Order-for-relief, confirmation, conversion, dismissal, hearing, board-vote,
    press-release and report dates never attach, so an involuntary case keeps
    its petition filing date (LABEL_POLICY 7) and an unrecoverable date stays
    None (LABEL_POLICY 8, 9). A compound "March 26 and 27, 2009" resolves to the
    earlier day, when the jointly filed case group commenced.
    """
    labelled = _labelled_petition_dates(section_text)
    if labelled:
        return labelled[0][0], "date:labelled" + (":compound" if labelled[0][1] else "")

    tiers: list[list[tuple[date, bool]]] = [[], []]
    for sentence in _split_sentences(section_text, _DATE_SENTENCE_ABBREVIATION):
        if not _is_date_petition_sentence(sentence):
            continue
        mentions = list(DATE_MENTION.finditer(sentence))
        for match in mentions:
            parsed = _parse_date_mention(match)
            if parsed is None or not _date_attaches_to_petition(sentence, match, mentions):
                continue
            tier = 0 if _registrant_is_debtor_in(sentence, ctx) else 1
            tiers[tier].append((parsed, bool(match.group("second"))))
            break
    for name, tier in zip(("date:registrant_sentence", "date:petition_sentence"), tiers):
        if tier:
            return tier[0][0], name + (":compound" if tier[0][1] else "")

    if full_text is not None and _PETITION_DATE_TERM.search(section_text):
        defined = _labelled_petition_dates(full_text)
        if defined:
            return defined[0][0], "date:defined_term" + (":compound" if defined[0][1] else "")
    return None, None


def _extract_petition_date(
    document_text: str, full_text: str | None = None, ctx: _IdentityContext | None = None
) -> date | None:
    """Parse the petition date into a real date, or return None.

    None is a census bucket, never a licence to substitute the disclosure date.
    """
    return _rank_petition_date(document_text, full_text, ctx)[0]


def _first_group(pattern: re.Pattern[str], document_text: str) -> str | None:
    match = pattern.search(document_text)
    return " ".join(match.group(1).split()) if match else None
