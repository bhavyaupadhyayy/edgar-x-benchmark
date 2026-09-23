"""Gate 1: unique bankruptcy events, positive 10-K observations, and the map.

Orchestrates the whole discovery chain. Nothing here is designed but unwired:

    submissions.zip -> 8-K and 8-K/A rows declaring item 1.03
      -> classify the Item 1.03 section only
      -> assemble events, merging amendments into one record per bankruptcy
      -> event time is the PETITION DATE, never the disclosure timestamp
      -> every same-CIK 10-K whose horizon contains the petition date
      -> FIRE exclusion on SIC as filed, with unknown SIC its own bucket
      -> bucket by the cohort year of each labelled 10-K

Two counts come out, and they are not the same number:

    unique events           bankruptcies
    positive observations   10-Ks those bankruptcies label

The event-to-observation map is written to disk because final Gate 2 needs the
real dependence structure, not a scalar duplicate rate. A bankruptcy can label
10-Ks in two different cohort years, which no scalar can represent.

Usage:
    python3 event_counts.py --submissions ./submissions.zip \
        --documents ./8k_text/ --dera ./dera_quarters/ --start 2012 --end 2024
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from bankruptcy_event import BankruptcyEvent, assemble_events
from constants import PREDICTION_HORIZON_DAYS, PRIMARY_COHORT_START_YEAR
from dera_sic import build_sic_index
from event_classification import Disposition, classify
from filing_history import SicEligibility, SubmissionsArchive, classify_sic
from observation_labels import label_observations
from submissions_scan import SubmissionsArchiveScanner

COUNTS_PATH = Path("event_counts.csv")
CENSUS_PATH = Path("disposition_census.csv")
MAPPING_PATH = Path("event_observation_map.json")


def build_gate_one(
    scanner: SubmissionsArchiveScanner,
    archive: SubmissionsArchive,
    documents: Path,
    start_year: int,
    end_year: int,
) -> tuple[list[dict], Counter[str], list[dict]]:
    census: Counter[str] = Counter()
    sources_by_cik = _group_sources_by_cik(scanner, archive, documents, census)

    events_by_cohort: Counter[int] = Counter()
    observations_by_cohort: Counter[int] = Counter()
    ambiguous_by_cohort: Counter[int] = Counter()
    mapping: list[dict] = []

    for cik, sources in sources_by_cik.items():
        for event in assemble_events(cik, sources):
            _process_event(
                event=event,
                archive=archive,
                start_year=start_year,
                end_year=end_year,
                census=census,
                events_by_cohort=events_by_cohort,
                observations_by_cohort=observations_by_cohort,
                ambiguous_by_cohort=ambiguous_by_cohort,
                mapping=mapping,
            )

    rows = [
        {
            "cohort_year": year,
            "unique_events": events_by_cohort[year],
            "positive_observations": observations_by_cohort[year],
            "ambiguous_observations": ambiguous_by_cohort[year],
        }
        for year in range(start_year, end_year + 1)
    ]
    return rows, census, mapping


def _group_sources_by_cik(
    scanner: SubmissionsArchiveScanner,
    archive: SubmissionsArchive,
    documents: Path,
    census: Counter[str],
) -> dict[int, list[tuple]]:
    """Classify every candidate filing and group it under its filer.

    Each filing is classified for the CIK it is listed under, with that
    registrant's EDGAR names in effect at acceptance, and flagged as co-registered
    when the same accession is listed under more than one CIK (LABEL_POLICY 11).
    """
    grouped: dict[int, list[tuple]] = defaultdict(list)
    candidates = list(scanner.scan_candidates())
    registrants_per_accession = Counter(candidate.accession for candidate in candidates)

    for candidate in candidates:
        census["item_1_03_filings"] += 1
        if candidate.is_amendment:
            census["amendment_filings"] += 1

        path = documents / f"{candidate.accession}.txt"
        if not path.exists():
            census["document_unavailable"] += 1
            continue

        profile = archive.profile(candidate.cik)
        co_registered = registrants_per_accession[candidate.accession] > 1
        if co_registered:
            census["co_registered_filings"] += 1
        classification = classify(
            path.read_text(errors="ignore"),
            registrant_names=profile.names_at(candidate.accepted_at) if profile else (),
            co_registered=co_registered,
        )
        census[f"filing_{classification.disposition.value}"] += 1
        grouped[candidate.cik].append(
            (
                candidate.accession,
                candidate.accepted_at,
                classification,
                candidate.is_amendment,
            )
        )

    return grouped


def _process_event(
    event: BankruptcyEvent,
    archive: SubmissionsArchive,
    start_year: int,
    end_year: int,
    census: Counter[str],
    events_by_cohort: Counter[int],
    observations_by_cohort: Counter[int],
    ambiguous_by_cohort: Counter[int],
    mapping: list[dict],
) -> None:
    census["assembled_events"] += 1
    census[f"event_{event.disposition.value}"] += 1

    if event.disposition in {Disposition.SUBSIDIARY_ONLY, Disposition.RECEIVERSHIP_ONLY}:
        return

    event_at = event.event_at
    if event_at is None:
        # No substituting the disclosure timestamp. An unparsed petition date
        # is a gap in the data, and pretending otherwise lengthens the horizon
        # by however long the filer took to disclose.
        census["event_date_unresolved"] += 1
        return

    profile = archive.profile(event.cik)
    if profile is None:
        census["no_filing_history"] += 1
        return

    labelling = label_observations(profile, event_at, PREDICTION_HORIZON_DAYS)
    if not labelling.is_eligible:
        census["eligibility_loss_no_predecessor_10k"] += 1
        return

    labelled_years: list[int] = []
    for filing in labelling.labelled_filings:
        cohort_year = filing.accepted_at.year
        eligibility = classify_sic(filing.sic_as_filed)

        # Cohort membership is decided FIRST, and independently of whether a SIC
        # could be joined. The DERA archives are only downloaded for the primary
        # window, so every observation outside it has sic_as_filed = None. With
        # the SIC test first, those were consumed by the unknown-SIC bucket and
        # observation_outside_cohort_window read zero: 494 out-of-window
        # observations were being reported as unknown SIC, against 13 genuine
        # in-window join misses. The bucket's name did not describe its contents.
        if not start_year <= cohort_year <= end_year:
            census["observation_outside_cohort_window"] += 1
            census[f"outside_window_{eligibility.value}"] += 1
            continue

        if eligibility is not SicEligibility.ELIGIBLE:
            census[f"observation_{eligibility.value}"] += 1
            if eligibility is SicEligibility.UNKNOWN:
                # Named explicitly because this is the only unknown-SIC figure
                # the paper may quote: a real DERA join miss on an observation
                # that is otherwise in scope.
                census["unknown_sic_in_primary_window"] += 1
            continue
        if event.disposition.is_positive:
            observations_by_cohort[cohort_year] += 1
        else:
            ambiguous_by_cohort[cohort_year] += 1
        labelled_years.append(cohort_year)

    if not labelled_years:
        return

    census["events_spanning_two_cohorts"] += int(len(set(labelled_years)) > 1)
    if event.disposition.is_positive:
        events_by_cohort[min(labelled_years)] += 1
    mapping.append(
        {
            "cik": event.cik,
            "disposition": event.disposition.value,
            "petition_date": event.petition_date.isoformat(),
            "docket": event.docket,
            "source_accessions": event.source_accessions,
            "labelled_cohort_years": labelled_years,
            "multiplicity": len(labelled_years),
        }
    )


def report(rows: list[dict], census: Counter[str], mapping: list[dict]) -> None:
    events = sum(row["unique_events"] for row in rows)
    observations = sum(row["positive_observations"] for row in rows)
    print("\nCohort year: unique events / positive observations")
    for row in rows:
        print(
            f"  {row['cohort_year']}: "
            f"{row['unique_events']:>4} / {row['positive_observations']:>4}"
        )

    print("\nCensus")
    for reason, count in census.most_common():
        print(f"  {reason}: {count}")

    # NOT called a lower/upper bound. A bound is a claim about where the truth
    # lies, and that claim rests on the classification rules being right about
    # which filings are registrant Chapter 7/11. The rules are unaudited, and
    # the real corpus has already shown errors in both directions. Until the
    # stratified manual audit is done these are rule outputs, nothing more.
    _print_multiplicity("rules-positive (UNVALIDATED)", mapping, positive_only=True)
    _print_multiplicity(
        "rules-positive + ambiguous (UNVALIDATED)", mapping, positive_only=False
    )
    print(f"Unique events {events}, positive observations {observations}")
    print(
        "\nNOTE: these are UNVALIDATED rule outputs, not bounds. Classification "
        "has not been\n      audited; do not quote them as lower/upper bounds."
    )
    print("\nPaste into power_analysis.py as fold_positive_counts:")
    print(f"  {tuple(row['positive_observations'] for row in rows)}")


def _print_multiplicity(label: str, mapping: list[dict], positive_only: bool) -> None:
    """Multiplicity for confirmed positives and for the upper-bound sample.

    Pooling ambiguous events into one figure mixes two populations whose
    filing behaviour differs, and the paper reports them apart.
    """
    entries = [
        entry
        for entry in mapping
        if not positive_only or entry["disposition"].startswith("registrant_")
    ]
    if not entries:
        print(f"\n{label}: no events")
        return
    counts = [entry["multiplicity"] for entry in entries]
    duplicated = sum(1 for count in counts if count > 1)
    print(
        f"\n{label}: {len(counts)} events, "
        f"mean multiplicity {sum(counts) / len(counts):.3f}, "
        f"duplicate rate {duplicated / len(counts):.3f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submissions", type=Path, required=True)
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--dera", type=Path, required=True)
    parser.add_argument("--start", type=int, default=PRIMARY_COHORT_START_YEAR)
    parser.add_argument("--end", type=int, default=2024)
    args = parser.parse_args()

    print("Building SIC index from DERA quarterly datasets", flush=True)
    sic_index = build_sic_index(args.dera)
    print(f"  {len(sic_index)} accessions indexed", flush=True)

    rows, census, mapping = build_gate_one(
        scanner=SubmissionsArchiveScanner(args.submissions),
        archive=SubmissionsArchive(args.submissions, sic_index),
        documents=args.documents,
        start_year=args.start,
        end_year=args.end,
    )
    report(rows, census, mapping)

    _write_csv(COUNTS_PATH, rows)
    _write_csv(
        CENSUS_PATH,
        [{"bucket": key, "count": value} for key, value in census.most_common()],
    )
    MAPPING_PATH.write_text(json.dumps(mapping, indent=2))
    print(f"\nWrote {COUNTS_PATH}, {CENSUS_PATH}, {MAPPING_PATH}")


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
