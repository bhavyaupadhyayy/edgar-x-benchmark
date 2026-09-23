"""Point-in-time extraction of Item 1A and Item 7 from a 10-K.

The text arms need two sections per filing: Item 1A Risk Factors and Item 7
Management's Discussion and Analysis. Both are delimited by sibling item
headings, and every practical difficulty is a boundary problem:

  - the table of contents repeats every heading, usually with dot leaders and a
    page number, and a naive first-match extractor returns the TOC entry;
  - Item 7 must stop at Item 7A, not run on into Item 8's financial statements,
    which would swamp the MD&A with tabular numerals;
  - Item 1A must stop at Item 1B, or Item 2 when 1B is absent;
  - smaller reporting companies are permitted to omit Item 1A entirely, so a
    missing section is a legitimate state and not an extraction failure;
  - some filings incorporate a section by reference in one sentence, which is
    present but substantively empty;
  - headings appear in inconsistent spellings: "ITEM 1A.", "Item 1A -",
    "Item 1A:", with non-breaking spaces and stray markup between token and
    number.

The strategy is therefore: enumerate every candidate start and every candidate
end, pair each start with its first following end, and keep the LONGEST
candidate section above a minimum length. A table-of-contents entry is
outscored by the real section automatically, without a heuristic that has to
recognise a TOC. Anything still below the minimum is reported missing rather
than passed on as text.

HTML is reduced to text with the same extractor the 8-K path uses, so the two
corpora are preprocessed identically.

`extract_sections` never raises on malformed input and never silently returns a
wrong section: every outcome is one of the reasons in `ExtractionOutcome`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from prepare_gate1_data import _TextExtractor

# A section shorter than this is a table-of-contents line, a cross-reference, or
# an incorporation by reference -- present, but not substantive text.
MIN_SECTION_CHARS = 1000

# Heading tokens tolerate markup debris, non-breaking spaces and punctuation
# between "Item" and its number.
_GAP = r"[\s \.\-:;\)\(]*"


def _heading(number: str) -> re.Pattern[str]:
    return re.compile(rf"^{_GAP}ITEM{_GAP}{number}\b", re.IGNORECASE | re.MULTILINE)


START_1A = _heading("1A")
END_1A = (_heading("1B"), _heading("2"))
START_7 = _heading("7")
END_7 = (_heading("7A"), _heading("8"))

# "Item 7" must not match "Item 7A" when locating the START of Item 7.
_ITEM_7A_AT = re.compile(rf"^{_GAP}ITEM{_GAP}7A\b", re.IGNORECASE)


class ExtractionOutcome:
    OK = "ok"
    NO_HEADING = "no_heading"
    NO_TERMINATOR = "no_terminator"
    TOO_SHORT = "too_short"
    EMPTY_DOCUMENT = "empty_document"


@dataclass(frozen=True)
class Section:
    outcome: str
    text: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome == ExtractionOutcome.OK

    def __len__(self) -> int:
        return len(self.text)


def html_to_text(payload: str) -> str:
    """Same reduction the 8-K corpus uses: block tags become newlines."""
    parser = _TextExtractor()
    try:
        parser.feed(payload)
        parser.close()
    except Exception:
        # Malformed markup must degrade, not crash. Whatever was parsed stands.
        pass
    text = parser.text()
    # Collapse runs of blank lines so heading anchors stay findable.
    return re.sub(r"\n{3,}", "\n\n", text)


def _candidate_starts(text: str, pattern: re.Pattern[str],
                      exclude_7a: bool = False) -> list[int]:
    starts = []
    for match in pattern.finditer(text):
        if exclude_7a:
            line_end = text.find("\n", match.start())
            line = text[match.start():line_end if line_end != -1 else len(text)]
            if _ITEM_7A_AT.match(line):
                continue
        starts.append(match.start())
    return starts


def _first_end_after(text: str, position: int,
                     patterns: tuple[re.Pattern[str], ...]) -> int | None:
    best = None
    for pattern in patterns:
        match = pattern.search(text, position)
        if match and (best is None or match.start() < best):
            best = match.start()
    return best


def _extract(text: str, start_pattern: re.Pattern[str],
             end_patterns: tuple[re.Pattern[str], ...],
             exclude_7a: bool = False) -> Section:
    if not text.strip():
        return Section(ExtractionOutcome.EMPTY_DOCUMENT)
    starts = _candidate_starts(text, start_pattern, exclude_7a)
    if not starts:
        return Section(ExtractionOutcome.NO_HEADING)

    best_text = ""
    saw_terminator = False
    for start in starts:
        # Skip past the heading line itself so the body begins at the content.
        body_start = text.find("\n", start)
        body_start = start if body_start == -1 else body_start + 1
        end = _first_end_after(text, body_start, end_patterns)
        if end is None:
            continue
        saw_terminator = True
        candidate = text[body_start:end].strip()
        if len(candidate) > len(best_text):
            best_text = candidate

    if not saw_terminator:
        return Section(ExtractionOutcome.NO_TERMINATOR)
    if len(best_text) < MIN_SECTION_CHARS:
        return Section(ExtractionOutcome.TOO_SHORT, best_text)
    return Section(ExtractionOutcome.OK, best_text)


def extract_item_1a(text: str) -> Section:
    """Item 1A Risk Factors, terminated by Item 1B or Item 2."""
    return _extract(text, START_1A, END_1A)


def extract_item_7(text: str) -> Section:
    """Item 7 MD&A, terminated by Item 7A or Item 8, never running into either."""
    return _extract(text, START_7, END_7, exclude_7a=True)


def extract_sections(payload: str, is_html: bool = True) -> dict[str, Section]:
    text = html_to_text(payload) if is_html else payload
    return {"item_1a": extract_item_1a(text), "item_7": extract_item_7(text)}


def count_candidate_headings(text: str) -> dict[str, int]:
    """Read-only diagnostic: how many candidate headings each anchor matched.

    Used by the coverage audit to flag duplicate-heading filings for QA review.
    It does not participate in extraction and cannot change any extracted
    section; `_extract` never consults it.
    """
    return {
        "item_1a_starts": len(_candidate_starts(text, START_1A)),
        "item_7_starts": len(_candidate_starts(text, START_7, exclude_7a=True)),
    }
