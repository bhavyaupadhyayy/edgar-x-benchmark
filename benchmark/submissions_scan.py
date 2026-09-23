"""Discovery from the SEC bulk submissions archive. No network, no search API.

The archive already carries the 8-K item codes each filer declared, so the
whole EDGAR full-text search layer is unnecessary. Scanning the archive removes
the pagination cap, the exhibit-duplicate problem, the undocumented endpoint,
and every network round trip after the one download.

    https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip

One caveat to validate before the counts gate anything: `items` is
filer-declared metadata. Its completeness should be checked against a
hand-verified sample, because a systematically blank field would look exactly
like an absence of bankruptcies.
"""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from constants import BANKRUPTCY_ITEM_CODE

PRIMARY_FILE_PATTERN = re.compile(r"^CIK(\d{10})\.json$")


@dataclass(frozen=True)
class BankruptcyCandidate:
    """One 8-K accession whose declared items include Item 1.03.

    Amendments are kept rather than dropped: an 8-K/A sometimes carries the
    petition date or docket number the original omitted. They are tagged so
    downstream event-level deduplication can collapse an original and its
    amendments into a single bankruptcy. Deduplicating on accession alone does
    NOT do this, because an amendment has its own accession.
    """

    cik: int
    accession: str
    accepted_at: datetime
    form: str
    primary_document: str | None = None

    @property
    def is_amendment(self) -> bool:
        return self.form.endswith("/A")

    @property
    def document_url(self) -> str | None:
        """Direct URL to the primary 8-K document.

        Built from the `primaryDocument` field the archive already carries, so
        no index lookup is needed. Returns None when the archive did not name a
        primary document; the caller reports that rather than guessing a
        filename.
        """
        if not self.primary_document:
            return None
        stripped = self.accession.replace("-", "")
        return (
            f"https://www.sec.gov/Archives/edgar/data/{self.cik}/"
            f"{stripped}/{self.primary_document}"
        )


class SubmissionsArchiveScanner:
    """Iterates every filer's complete history inside the bulk archive."""

    def __init__(self, archive_path: Path):
        self._archive_path = archive_path

    def scan_candidates(self) -> Iterator[BankruptcyCandidate]:
        """Yield unique Item 1.03 8-K accessions across all filers."""
        with zipfile.ZipFile(self._archive_path) as archive:
            names = archive.namelist()
            index = _build_history_index(names)
            for primary_name, extra_names in index.items():
                match = PRIMARY_FILE_PATTERN.match(primary_name)
                if match is None:
                    continue
                cik = int(match.group(1))
                seen: set[str] = set()
                for block in _history_blocks(archive, primary_name, extra_names):
                    for candidate in _candidates_from_block(cik, block):
                        if candidate.accession in seen:
                            continue
                        seen.add(candidate.accession)
                        yield candidate


def _build_history_index(names: list[str]) -> dict[str, list[str]]:
    """Map each primary CIK file to its auxiliary historical files.

    Older filings live outside `filings.recent`, in files named
    CIK##########-submissions-###.json. Ignoring them makes early-cohort
    history invisible.
    """
    primaries = [name for name in names if PRIMARY_FILE_PATTERN.match(name)]
    index: dict[str, list[str]] = {name: [] for name in primaries}
    for name in names:
        if "-submissions-" not in name:
            continue
        primary = f"{name.split('-submissions-')[0]}.json"
        if primary in index:
            index[primary].append(name)
    return index


def _history_blocks(
    archive: zipfile.ZipFile, primary_name: str, extra_names: list[str]
) -> Iterator[dict]:
    primary = _read_json(archive, primary_name)
    filings = primary.get("filings", {})
    yield filings.get("recent", {})
    for extra_name in extra_names:
        yield _read_json(archive, extra_name)


def _candidates_from_block(cik: int, block: dict) -> Iterator[BankruptcyCandidate]:
    forms = block.get("form", [])
    items = block.get("items", [])
    accessions = block.get("accessionNumber", [])
    accepted = block.get("acceptanceDateTime", [])
    filed = block.get("filingDate", [])
    primary = block.get("primaryDocument", [])

    for position, form in enumerate(forms):
        if not form.startswith("8-K"):
            continue
        declared = items[position] if position < len(items) else ""
        if BANKRUPTCY_ITEM_CODE not in _split_items(declared):
            continue
        timestamp = parse_timestamp(
            accepted[position] if position < len(accepted) else None,
            filed[position] if position < len(filed) else None,
        )
        if timestamp is None:
            continue
        yield BankruptcyCandidate(
            cik=cik,
            accession=accessions[position],
            accepted_at=timestamp,
            form=form,
            primary_document=(
                primary[position] if position < len(primary) else None
            ),
        )


def _split_items(declared: str) -> set[str]:
    return {piece.strip() for piece in declared.split(",") if piece.strip()}


def parse_timestamp(accepted: str | None, filed: str | None) -> datetime | None:
    """Prefer the acceptance timestamp; fall back to the filing date.

    Fallbacks should be counted and reported: they mean the observation is
    timed less precisely than the point-in-time contract requires.
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


def _read_json(archive: zipfile.ZipFile, name: str) -> dict:
    with archive.open(name) as handle:
        return json.loads(handle.read().decode("utf-8"))
