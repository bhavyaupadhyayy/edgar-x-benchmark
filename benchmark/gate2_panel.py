"""Gate 2 pilot, stage 2: build the paired observation panel.

One row per 10-K observation, carrying two feature vectors over the *same*
observation and the *same* ratio definitions:

  Arm A, strict point-in-time
      A fact for fiscal period P may come only from a submission accepted at or
      before this 10-K's own EDGAR acceptance timestamp. Where several qualify,
      the latest one wins -- that is what a real-time user would have had.
      Industry is the SIC as filed on this submission. Industry medians are
      computed from the training fold only.

  Arm B, contaminated / restated
      The same fact may come from any submission reporting period P, including
      ones filed years later. The latest filed wins, so restatements beat
      originals. This is not a strawman: it is the documented behaviour of
      `EdgarClient.get_fundamentals_history` (PIT contract section 2), the
      production path this study exists to price. Industry is the registrant's
      present-day SIC, and industry medians are pooled over the whole panel,
      including the test cohort and years after it.

Membership is identical between arms by construction: the universe, the label
and the train/test split are computed once and shared. Only the values behind
the ratios differ. Survivorship contamination is deliberately NOT exercised
here -- it changes who is in the panel, which would break the pairing the
paired bootstrap depends on.

    python3 gate2_panel.py
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from constants import PREDICTION_HORIZON_DAYS, PRIMARY_COHORT_START_YEAR
from filing_history import SicEligibility, classify_sic

GATE2_DIR = Path("outputs/gate2")
EVENT_MAP_PATH = Path("event_observation_map.json")
END_YEAR = 2024

POSITIVE_DISPOSITIONS = {"registrant_chapter_11", "registrant_chapter_7"}

# Revenue and operating cash flow are reported under more than one tag across
# vintages; first present wins, in preference order.
REVENUE_TAGS = (
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
)
OCF_TAGS = (
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
)

RATIO_NAMES = [
    "wc_to_assets",
    "re_to_assets",
    "ebit_to_assets",
    "ni_to_assets",
    "rev_to_assets",
    "equity_to_assets",
    "liab_to_assets",
    "current_ratio",
    "cash_to_assets",
    "ocf_to_assets",
    "interest_coverage",
    "log_assets",
    "negative_equity",
    "ebit_vs_industry",
    "liab_vs_industry",
]

# Ratios are unbounded in the tails when a denominator approaches zero, and a
# single 10^9 leverage ratio would dominate a standardised linear model. These
# are winsorisation limits, applied identically to both arms.
CLIPS = {
    "wc_to_assets": (-5.0, 2.0),
    "re_to_assets": (-10.0, 2.0),
    "ebit_to_assets": (-5.0, 2.0),
    "ni_to_assets": (-5.0, 2.0),
    "rev_to_assets": (0.0, 10.0),
    "equity_to_assets": (-5.0, 2.0),
    "liab_to_assets": (0.0, 10.0),
    "current_ratio": (0.0, 20.0),
    "cash_to_assets": (0.0, 1.0),
    "ocf_to_assets": (-5.0, 2.0),
    "interest_coverage": (-50.0, 50.0),
    "log_assets": (0.0, 30.0),
    "negative_equity": (0.0, 1.0),
    "ebit_vs_industry": (-5.0, 5.0),
    "liab_vs_industry": (-10.0, 10.0),
}


def parse_accepted(value: str) -> datetime | None:
    value = (value or "").strip()
    for layout in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, layout)
        except ValueError:
            continue
    return None


def load_submissions() -> list[dict]:
    rows = []
    with (GATE2_DIR / "submissions.csv").open() as handle:
        for row in csv.DictReader(handle):
            accepted = parse_accepted(row["accepted"])
            if accepted is None:
                continue
            try:
                cik = int(row["cik"])
            except (TypeError, ValueError):
                continue
            row["cik"] = cik
            row["accepted_at"] = accepted
            rows.append(row)
    return rows


def load_facts() -> dict[str, dict[tuple[str, str], float]]:
    """adsh -> {(tag, ddate): value}, keeping the right duration per tag."""
    facts: dict[str, dict[tuple[str, str], float]] = defaultdict(dict)
    with (GATE2_DIR / "facts.csv").open() as handle:
        for row in csv.DictReader(handle):
            tag = row["tag"]
            qtrs = row["qtrs"]
            # Balance-sheet tags are instants; flow tags are annual durations.
            wanted = "0" if tag in INSTANT else "4"
            if qtrs != wanted:
                continue
            try:
                value = float(row["value"])
            except (TypeError, ValueError):
                continue
            facts[row["adsh"]][(tag, row["ddate"])] = value
    return facts


INSTANT = {
    "Assets", "AssetsCurrent", "Liabilities", "LiabilitiesCurrent",
    "StockholdersEquity", "RetainedEarningsAccumulatedDeficit",
    "CashAndCashEquivalentsAtCarryingValue", "LiabilitiesAndStockholdersEquity",
}


def load_positive_events() -> list[tuple[int, datetime]]:
    events = json.loads(EVENT_MAP_PATH.read_text())
    positives = []
    for event in events:
        if event.get("disposition") not in POSITIVE_DISPOSITIONS:
            continue
        raw = event.get("petition_date")
        if not raw:
            continue
        positives.append((int(event["cik"]), datetime.strptime(raw, "%Y-%m-%d")))
    return positives


def safe_div(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def pick(values: dict, tags, ddate):
    for tag in tags:
        got = values.get((tag, ddate))
        if got is not None:
            return got
    return None


def build_vector(values: dict, ddate: str) -> dict | None:
    """Raw ratios from one already-resolved fact bundle. None if unusable."""
    assets = values.get(("Assets", ddate))
    if assets is None or assets <= 0:
        assets = values.get(("LiabilitiesAndStockholdersEquity", ddate))
    if assets is None or assets <= 0:
        return None

    current_assets = values.get(("AssetsCurrent", ddate))
    current_liabilities = values.get(("LiabilitiesCurrent", ddate))
    liabilities = values.get(("Liabilities", ddate))
    equity = values.get(("StockholdersEquity", ddate))
    if liabilities is None and equity is not None:
        liabilities = assets - equity
    if equity is None and liabilities is not None:
        equity = assets - liabilities

    retained = values.get(("RetainedEarningsAccumulatedDeficit", ddate))
    cash = values.get(("CashAndCashEquivalentsAtCarryingValue", ddate))
    revenue = pick(values, REVENUE_TAGS, ddate)
    net_income = values.get(("NetIncomeLoss", ddate))
    ebit = values.get(("OperatingIncomeLoss", ddate))
    interest = values.get(("InterestExpense", ddate))
    ocf = pick(values, OCF_TAGS, ddate)

    working_capital = None
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities

    import math

    return {
        "wc_to_assets": safe_div(working_capital, assets),
        "re_to_assets": safe_div(retained, assets),
        "ebit_to_assets": safe_div(ebit, assets),
        "ni_to_assets": safe_div(net_income, assets),
        "rev_to_assets": safe_div(revenue, assets),
        "equity_to_assets": safe_div(equity, assets),
        "liab_to_assets": safe_div(liabilities, assets),
        "current_ratio": safe_div(current_assets, current_liabilities),
        "cash_to_assets": safe_div(cash, assets),
        "ocf_to_assets": safe_div(ocf, assets),
        "interest_coverage": safe_div(ebit, interest) if interest else None,
        "log_assets": math.log10(assets),
        "negative_equity": None if equity is None else float(equity < 0),
    }


def main() -> int:
    if not (GATE2_DIR / "facts.csv").exists():
        print("run gate2_extract.py first", file=sys.stderr)
        return 1

    print("loading submissions index")
    submissions = load_submissions()
    print(f"  {len(submissions)} submissions")

    # Every submission a CIK ever made that reports a given period end, in
    # acceptance order. This is what both arms select from; they differ only in
    # where the selection is allowed to stop.
    by_cik: dict[int, list[dict]] = defaultdict(list)
    for row in submissions:
        by_cik[row["cik"]].append(row)
    for rows in by_cik.values():
        rows.sort(key=lambda row: row["accepted_at"])

    present_day_sic: dict[int, int | None] = {}
    for cik, rows in by_cik.items():
        for row in reversed(rows):
            try:
                present_day_sic[cik] = int(row["sic"])
                break
            except (TypeError, ValueError):
                continue
        present_day_sic.setdefault(cik, None)

    print("loading facts")
    facts = load_facts()
    print(f"  {len(facts)} submissions carry usable facts")

    print("loading positive events")
    positives = load_positive_events()
    print(f"  {len(positives)} rules-positive events with a petition date")
    events_by_cik: dict[int, list[datetime]] = defaultdict(list)
    for cik, event_at in positives:
        events_by_cik[cik].append(event_at)

    # --- observation universe, identical for both arms ----------------------
    census: dict[str, int] = defaultdict(int)
    rows_out = []
    for row in submissions:
        if row["form"] != "10-K":
            continue
        census["tenk_submissions"] += 1
        accepted = row["accepted_at"]
        cohort_year = accepted.year
        if not PRIMARY_COHORT_START_YEAR <= cohort_year <= END_YEAR:
            census["outside_cohort_window"] += 1
            continue
        try:
            sic_as_filed = int(row["sic"])
        except (TypeError, ValueError):
            sic_as_filed = None
        eligibility = classify_sic(sic_as_filed)
        if eligibility is not SicEligibility.ELIGIBLE:
            census[f"excluded_{eligibility.value}"] += 1
            continue
        period = (row["period"] or "").strip()
        if not period:
            census["no_period"] += 1
            continue

        cik = row["cik"]

        # Arm A: only submissions accepted at or before this one may speak.
        pit_values: dict = {}
        for other in by_cik[cik]:
            if other["accepted_at"] > accepted:
                break
            pit_values.update(facts.get(other["adsh"], {}))
        # Arm B: every submission may speak, latest filed wins.
        restated_values: dict = {}
        for other in by_cik[cik]:
            restated_values.update(facts.get(other["adsh"], {}))

        pit_vector = build_vector(pit_values, period)
        restated_vector = build_vector(restated_values, period)
        if pit_vector is None or restated_vector is None:
            census["no_usable_assets_in_both_arms"] += 1
            continue

        horizon_end = accepted + timedelta(days=PREDICTION_HORIZON_DAYS)
        label = int(any(accepted < event_at < horizon_end
                        for event_at in events_by_cik.get(cik, ())))

        census["observations"] += 1
        census["positives"] += label
        rows_out.append({
            "adsh": row["adsh"],
            "cik": cik,
            "cohort_year": cohort_year,
            "accepted_at": accepted.isoformat(),
            "period": period,
            "sic_as_filed": sic_as_filed,
            "sic_present_day": present_day_sic.get(cik),
            "label": label,
            "pit": pit_vector,
            "restated": restated_vector,
        })

    print("\nuniverse census")
    for name, count in sorted(census.items()):
        print(f"  {name:36s} {count}")

    out_path = GATE2_DIR / "panel.jsonl"
    with out_path.open("w") as handle:
        for row in rows_out:
            handle.write(json.dumps(row) + "\n")
    print(f"\nwrote {out_path} ({len(rows_out)} rows)")

    by_year: dict[int, list[int]] = defaultdict(list)
    for row in rows_out:
        by_year[row["cohort_year"]].append(row["label"])
    print("\ncohort_year  observations  positives")
    for year in sorted(by_year):
        labels = by_year[year]
        print(f"  {year}      {len(labels):7d}   {sum(labels):5d}")

    # How often does the restated arm actually differ? If this were near zero
    # the whole experiment would be measuring noise.
    differing = 0
    for row in rows_out:
        for name in RATIO_NAMES[:13]:
            a, b = row["pit"].get(name), row["restated"].get(name)
            if a is None or b is None:
                if a is not b:
                    differing += 1
                    break
            elif abs(a - b) > 1e-9:
                differing += 1
                break
    share = differing / len(rows_out) if rows_out else 0.0
    print(f"\nobservations whose raw ratios differ between arms: "
          f"{differing} ({share:.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
