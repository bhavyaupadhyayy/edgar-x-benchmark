"""Acquire exactly the data Gate 1 needs, and nothing else.

Four stages, each resumable and each refusing to proceed on incomplete input:

  1. SEC bulk submissions archive
  2. DERA Financial Statement Data Set quarters covering the cohort window
  3. Item 1.03 candidates discovered from the archive, offline
  4. Primary 8-K documents for those candidates only

Stage 4 is candidate-sized by construction. The full EDGAR corpus is never
touched: candidates come from archive metadata, so only filings that declared
Item 1.03 are ever fetched.

Endpoints verified against SEC's own documentation pages, September 2026.

    python3 prepare_gate1_data.py --email you@domain.com
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from constants import PRIMARY_COHORT_START_YEAR
from sec_download import DownloadError, DownloadStats, SecClient
from submissions_scan import SubmissionsArchiveScanner

SUBMISSIONS_URL = (
    "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
)
DERA_URL_TEMPLATE = (
    "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{quarter}.zip"
)

DEFAULT_END_YEAR = 2024
SUBMISSIONS_PATH = Path("submissions.zip")
DERA_DIR = Path("dera_quarters")
DOCUMENTS_DIR = Path("8k_text")

# A run finding no Item 1.03 filings across a decade means a broken scan, not a
# decade without bankruptcies.
MIN_PLAUSIBLE_CANDIDATES = 100

# Below this share of documents retrieved, Gate 1's census would be dominated
# by fetch failures rather than by the data.
MIN_DOCUMENT_SUCCESS_RATE = 0.95


# Block-level tags must become line breaks. The classifier anchors item
# headings with a multiline ^\s*Item pattern, so collapsing an 8-K into one
# line would make every heading unfindable and send the whole corpus into the
# ambiguous bucket.
BLOCK_TAGS = {
    "p", "div", "br", "tr", "td", "th", "table", "li", "ul", "ol",
    "h1", "h2", "h3", "h4", "h5", "h6", "section", "hr",
}
SKIP_TAGS = {"script", "style"}


class _TextExtractor(HTMLParser):
    """Strip tags so the classifier sees prose, not markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skipping = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP_TAGS:
            self._skipping = True
        elif tag in BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            self._skipping = False
        elif tag in BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skipping:
            self._chunks.append(data)

    def text(self) -> str:
        collapsed = re.sub(r"[ \t\r\f\v]+", " ", "".join(self._chunks))
        return re.sub(r"\n\s*\n+", "\n", collapsed).strip()


def required_quarters(start_year: int, end_year: int) -> list[str]:
    """Quarters covering every 10-K acceptance inside the cohort window."""
    return [
        f"{year}q{quarter}"
        for year in range(start_year, end_year + 1)
        for quarter in range(1, 5)
    ]


def fetch_submissions(client: SecClient, stats: DownloadStats) -> bool:
    try:
        outcome = client.download_to(SUBMISSIONS_URL, SUBMISSIONS_PATH, expect_zip=True)
    except DownloadError as error:
        stats.record_failure("submissions.zip", str(error))
        return False
    _count(stats, outcome)
    print(f"submissions archive: {outcome}", flush=True)
    return True


def fetch_dera(client: SecClient, quarters: list[str], stats: DownloadStats) -> int:
    present = 0
    for quarter in quarters:
        destination = DERA_DIR / f"{quarter}.zip"
        try:
            outcome = client.download_to(
                DERA_URL_TEMPLATE.format(quarter=quarter), destination, expect_zip=True
            )
        except DownloadError as error:
            stats.record_failure(f"dera/{quarter}", str(error))
            print(f"  {quarter}: FAILED {error}", flush=True)
            continue
        _count(stats, outcome)
        present += 1
        print(f"  {quarter}: {outcome}", flush=True)
    return present


def discover_candidates() -> list:
    """Offline scan of the archive for Item 1.03 filings."""
    scanner = SubmissionsArchiveScanner(SUBMISSIONS_PATH)
    candidates = list(scanner.scan_candidates())
    print(f"Item 1.03 candidate accessions: {len(candidates)}", flush=True)
    return candidates


def fetch_documents(client: SecClient, candidates: list, stats: DownloadStats) -> int:
    """Fetch only the primary document of each candidate, as plain text."""
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    saved = 0

    for position, candidate in enumerate(candidates, start=1):
        destination = DOCUMENTS_DIR / f"{candidate.accession}.txt"
        if destination.exists() and destination.stat().st_size > 0:
            stats.cached += 1
            saved += 1
            continue

        url = candidate.document_url
        if url is None:
            stats.record_failure(candidate.accession, "archive named no primary document")
            continue
        try:
            payload = client.fetch(url)
        except DownloadError as error:
            stats.record_failure(candidate.accession, str(error))
            continue

        text = _to_text(payload)
        if len(text.strip()) < 200:
            stats.record_failure(candidate.accession, "document body implausibly short")
            continue

        partial = destination.with_suffix(".txt.part")
        partial.write_text(text, encoding="utf-8")
        partial.replace(destination)
        stats.downloaded += 1
        saved += 1

        if position % 250 == 0:
            print(f"  documents {position}/{len(candidates)}", flush=True)

    return saved


def summarize(
    quarters: list[str], present: int, candidates: int, saved: int, stats: DownloadStats
) -> bool:
    print("\n=== ACQUISITION SUMMARY ===")
    print(f"submissions archive:            {'OK' if SUBMISSIONS_PATH.exists() else 'MISSING'}")
    print(f"DERA quarters expected:         {len(quarters)}")
    print(f"DERA quarters present:          {present}")
    print(f"Item 1.03 candidate accessions: {candidates}")
    print(f"primary documents expected:     {candidates}")
    print(f"primary documents available:    {saved}")
    print(f"failed downloads:               {stats.failed}")

    if stats.failures:
        print("\nfailures (first 20):")
        for failure in stats.failures[:20]:
            print(f"  {failure}")

    problems = _problems(
        quarters, present, candidates, saved, SUBMISSIONS_PATH.exists()
    )
    for problem in problems:
        print(f"\nBLOCKER: {problem}")
    return not problems


def _problems(
    quarters,
    present: int,
    candidates: int,
    saved: int,
    submissions_present: bool,
) -> list[str]:
    """Blockers, decided from arguments alone so the verdict is testable."""
    problems = []
    if not submissions_present:
        problems.append("submissions archive missing; Gate 1 cannot run")
    if present < len(quarters):
        problems.append(
            f"{len(quarters) - present} DERA quarters missing; SIC as filed would be "
            "unknown for those cohorts and the FIRE exclusion would silently weaken"
        )
    if candidates < MIN_PLAUSIBLE_CANDIDATES:
        problems.append(
            f"only {candidates} Item 1.03 candidates found; a decade of filings cannot "
            "plausibly contain so few, so treat the scan as broken"
        )
    if candidates and saved / candidates < MIN_DOCUMENT_SUCCESS_RATE:
        problems.append(
            f"only {saved}/{candidates} documents retrieved; the census would measure "
            "fetch failures rather than bankruptcies"
        )
    return problems


def _to_text(payload: bytes) -> str:
    extractor = _TextExtractor()
    extractor.feed(payload.decode("utf-8", errors="ignore"))
    return extractor.text()


def _count(stats: DownloadStats, outcome: str) -> None:
    if outcome == "cached":
        stats.cached += 1
    else:
        stats.downloaded += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Contact address for SEC User-Agent")
    parser.add_argument("--start", type=int, default=PRIMARY_COHORT_START_YEAR)
    parser.add_argument("--end", type=int, default=DEFAULT_END_YEAR)
    args = parser.parse_args()

    try:
        client = SecClient(f"EDGAR-X Research {args.email}")
    except DownloadError as error:
        sys.exit(f"BLOCKER: {error}")

    stats = DownloadStats()
    quarters = required_quarters(args.start, args.end)

    print("[1/4] SEC bulk submissions archive", flush=True)
    if not fetch_submissions(client, stats):
        summarize(quarters, 0, 0, 0, stats)
        sys.exit(1)

    print(f"\n[2/4] DERA quarters ({len(quarters)} needed)", flush=True)
    present = fetch_dera(client, quarters, stats)

    print("\n[3/4] Discovering Item 1.03 candidates (offline)", flush=True)
    candidates = discover_candidates()

    print("\n[4/4] Primary 8-K documents for candidates only", flush=True)
    saved = fetch_documents(client, candidates, stats)

    ready = summarize(quarters, present, len(candidates), saved, stats)
    print("\nREADY FOR GATE 1" if ready else "\nNOT READY: fix the blockers above")
    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()
