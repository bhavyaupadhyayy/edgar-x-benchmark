"""SIC as filed, joined from the DERA Financial Statement Data Sets.

`filing_history.py` can only see a filer's present-day SIC. Applying that to a
2013 observation leaks a 2026 classification backward, which is the exact error
class the study exists to measure. The per-submission SIC lives in the `sub.txt`
table of each quarterly Financial Statement Data Set, keyed by accession.

Download the quarterly archives once from the SEC DERA page, point this at the
directory, and the accession -> SIC map is built locally.

Without this join the FIRE exclusion silently excludes nothing, because
`sic_as_filed` is None and the exclusion treats None as "not FIRE".
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

SUB_TABLE_NAME = "sub.txt"
ACCESSION_COLUMN = "adsh"
SIC_COLUMN = "sic"


def build_sic_index(dataset_dir: Path) -> dict[str, int]:
    """Map accession number to the SIC assigned at submission time.

    Accepts a directory of quarterly Financial Statement Data Set zips
    (2012q1.zip and so on). Later quarters win on the rare duplicate accession.
    """
    index: dict[str, int] = {}
    for archive_path in sorted(dataset_dir.glob("*.zip")):
        index.update(_read_quarter(archive_path))
    return index


def _read_quarter(archive_path: Path) -> dict[str, int]:
    quarter: dict[str, int] = {}
    with zipfile.ZipFile(archive_path) as archive:
        if SUB_TABLE_NAME not in archive.namelist():
            return quarter
        with archive.open(SUB_TABLE_NAME) as handle:
            text = io.TextIOWrapper(handle, encoding="latin-1", newline="")
            for row in csv.DictReader(text, delimiter="\t"):
                sic = _parse_sic(row.get(SIC_COLUMN))
                accession = row.get(ACCESSION_COLUMN)
                if sic is not None and accession:
                    quarter[accession] = sic
    return quarter


def _parse_sic(value: str | None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None
