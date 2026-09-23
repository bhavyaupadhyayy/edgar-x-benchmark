"""Verify the shipped artifact, not the working directory.

The previous revision passed every integration assertion locally and shipped a
package missing two modules. Integration tests prove the code works where it
was written; this proves it works where it lands.

Builds the zip from an explicit manifest, extracts it into an empty directory,
asserts the manifest survived, and runs the integration test from there.

    python3 package_test.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

MANIFEST = (
    "README.md",
    "acquisition_test.py",
    "bankruptcy_event.py",
    "constants.py",
    "dera_sic.py",
    "event_classification.py",
    "event_counts.py",
    "filing_history.py",
    "integration_test.py",
    "observation_labels.py",
    "package_test.py",
    "panel_simulation.py",
    "power_analysis.py",
    "prepare_gate1_data.py",
    "requirements.txt",
    "sec_download.py",
    "submissions_scan.py",
)

ARCHIVE_NAME = "edgar-x-bench.zip"

# Both suites run from the extracted directory, not the working copy.
SUITES = ("integration_test.py", "acquisition_test.py")


def build_archive(source: Path, destination: Path) -> list[str]:
    """Zip exactly the manifest, reporting anything the manifest is missing."""
    missing = [name for name in MANIFEST if not (source / name).exists()]
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in MANIFEST:
            if (source / name).exists():
                archive.write(source / name, arcname=name)
    return missing


def verify(archive_path: Path) -> bool:
    with tempfile.TemporaryDirectory() as raw_target:
        target = Path(raw_target)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(target)

        extracted = {path.name for path in target.iterdir()}
        absent = [name for name in MANIFEST if name not in extracted]
        for name in MANIFEST:
            print(f"{'PASS' if name in extracted else 'FAIL'}  shipped: {name}")
        if absent:
            return False

        return all(_run_suite(target, name) for name in SUITES)


def _run_suite(target: Path, name: str) -> bool:
    result = subprocess.run(
        [sys.executable, name], cwd=target, capture_output=True, text=True
    )
    print(f"\n--- {name} ---")
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip())
    return result.returncode == 0


def main() -> None:
    source = Path(__file__).parent.resolve()
    archive_path = source / ARCHIVE_NAME
    missing = build_archive(source, archive_path)
    for name in missing:
        print(f"FAIL  manifest names a file that does not exist: {name}")

    passed = verify(archive_path) and not missing
    print(f"\n{'PACKAGE OK' if passed else 'PACKAGE BROKEN'}: {archive_path.name}")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
