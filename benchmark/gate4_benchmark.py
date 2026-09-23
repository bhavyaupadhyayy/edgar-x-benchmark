"""The frozen EDGAR-X benchmark: arms A, B and C over rolling cohorts.

Everything here is fixed by FINAL_BENCHMARK_PROTOCOL.md and its Amendment 1.
Nothing in this file may be changed once the first model is trained.

    Arm A  strict-PIT financial ratios only (15 features)
    Arm B  strict-PIT Item 1A + Item 7 sparse text only, two separately fitted
           TF-IDF blocks at 100,000 features each, plus 2 missingness indicators
    Arm C  ratios + both text blocks + indicators, one logistic regression;
           no stacking, no ensemble

Populations:
    B    primary, the full frozen Gate 1 panel
    A    sensitivity, all 188 validation CIKs removed
    DUP  sensitivity, the 8 observations in byte-identical cross-target
         duplicate pairs removed

Regularisation: one rule for all three arms, C in {0.01, 0.1, 1.0, 10.0}, chosen
on an inner validation window of the most recent contiguous prior cohorts holding
at least 25 positives, with candidate models trained only on cohorts preceding
that window, and the preregistered C=1.0 fallback when no such split exists.
Vectorisers are fitted on the OUTER TRAINING PERIOD ONLY. The outer test cohort
never touches selection.

Resumable: each (population, cohort) unit writes its own predictions file and is
skipped if already present.

    python3 gate4_benchmark.py [--population B|A|DUP] [--cohort YYYY]
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

from gate2_pilot import GATE2_DIR, MODEL_KWARGS, build_matrix, standardise

CACHE_DIR = Path("10k_sections")
GATE3_DIR = Path("outputs/gate3")
OUT_DIR = Path("outputs/gate4")

COHORTS = tuple(range(2013, 2025))
C_GRID = (0.01, 0.1, 1.0, 10.0)
C_FALLBACK = 1.0
INNER_MIN_POSITIVES = 25
MAX_FEATURES_PER_SECTION = 100_000

VECTORIZER_KWARGS = dict(lowercase=True, stop_words="english",
                         ngram_range=(1, 2), sublinear_tf=True, min_df=5,
                         max_features=MAX_FEATURES_PER_SECTION)

ARMS = ("A_ratios", "B_text", "C_combined")


def load_panel() -> list[dict]:
    with (GATE2_DIR / "panel.jsonl").open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validation_ciks() -> set[int]:
    with open("final_validation_sample.csv") as handle:
        return {int(row["cik"]) for row in csv.DictReader(handle)}


def duplicate_accessions() -> set[str]:
    path = GATE3_DIR / "duplicate_content_pairs.json"
    return {row["accession"] for row in json.loads(path.read_text())}


def population(name: str, panel: list[dict]) -> list[dict]:
    if name == "B":
        return panel
    if name == "A":
        excluded = validation_ciks()
        return [row for row in panel if row["cik"] not in excluded]
    if name == "DUP":
        excluded = duplicate_accessions()
        return [row for row in panel if row["adsh"] not in excluded]
    raise SystemExit(f"unknown population {name}")


def sections_for(adsh: str) -> dict:
    path = CACHE_DIR / f"{adsh}.json.gz"
    if not path.exists():
        return {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


class TextCorpus:
    """Lazy per-section text, so a fit never holds the whole corpus in memory."""

    def __init__(self, rows: list[dict], section: str):
        self.rows = rows
        self.section = section

    def __iter__(self):
        for row in self.rows:
            yield sections_for(row["adsh"]).get(self.section, "")

    def __len__(self) -> int:
        return len(self.rows)


def missingness(rows: list[dict]) -> np.ndarray:
    flags = np.zeros((len(rows), 2))
    for index, row in enumerate(rows):
        stored = sections_for(row["adsh"])
        flags[index, 0] = 0.0 if "item_1a" in stored else 1.0
        flags[index, 1] = 0.0 if "item_7" in stored else 1.0
    return flags


def inner_split(rows: list[dict], test_year: int):
    """Most recent contiguous prior cohorts holding >= 25 positives."""
    positives = {}
    for row in rows:
        if row["cohort_year"] < test_year:
            positives[row["cohort_year"]] = (
                positives.get(row["cohort_year"], 0) + row["label"])
    prior = sorted(positives)
    window, total = [], 0
    for year in reversed(prior):
        window.insert(0, year)
        total += positives[year]
        if total >= INNER_MIN_POSITIVES:
            break
    if not window or total < INNER_MIN_POSITIVES:
        return None, None
    inner_train_years = [year for year in prior if year < window[0]]
    if not inner_train_years:
        return None, None
    return inner_train_years, window


def build_features(arm: str, fit_rows: list[dict], target_rows: list[dict],
                   vectorizers=None):
    """Feature matrix for one arm. Vectorisers are fitted on `fit_rows` only."""
    blocks = []
    if arm in ("A_ratios", "C_combined"):
        train_x = build_matrix(fit_rows, "pit", fit_rows)
        target_x = build_matrix(target_rows, "pit", fit_rows)
        _, scaled = standardise(train_x, target_x)
        blocks.append(sparse.csr_matrix(scaled))
    if arm in ("B_text", "C_combined"):
        if vectorizers is None:
            raise ValueError("text arms need fitted vectorizers")
        for section in ("item_1a", "item_7"):
            blocks.append(vectorizers[section].transform(
                TextCorpus(target_rows, section)))
        blocks.append(sparse.csr_matrix(missingness(target_rows)))
    return sparse.hstack(blocks, format="csr")


def fit_vectorizers(fit_rows: list[dict]) -> dict:
    fitted = {}
    for section in ("item_1a", "item_7"):
        started = time.time()
        vectorizer = TfidfVectorizer(**VECTORIZER_KWARGS)
        vectorizer.fit(TextCorpus(fit_rows, section))
        fitted[section] = vectorizer
        print(f"      vectorizer {section}: "
              f"{len(vectorizer.vocabulary_)} features "
              f"[{time.time() - started:.0f}s]", flush=True)
    return fitted


def select_c(arm: str, rows: list[dict], test_year: int, vectorizers):
    """Choose C on prior cohorts only. Returns (C, provenance string)."""
    inner_train_years, window = inner_split(rows, test_year)
    if inner_train_years is None:
        return C_FALLBACK, "fallback_no_inner_split"
    inner_train = [row for row in rows if row["cohort_year"] in inner_train_years]
    inner_valid = [row for row in rows if row["cohort_year"] in window]
    train_x = build_features(arm, inner_train, inner_train, vectorizers)
    valid_x = build_features(arm, inner_train, inner_valid, vectorizers)
    train_y = np.array([row["label"] for row in inner_train])
    valid_y = np.array([row["label"] for row in inner_valid])
    best_c, best_ap = C_FALLBACK, -1.0
    for candidate in C_GRID:
        model = LogisticRegression(**{**MODEL_KWARGS, "C": candidate})
        model.fit(train_x, train_y)
        score = model.predict_proba(valid_x)[:, 1]
        ap = average_precision_score(valid_y, score)
        if ap > best_ap:
            best_ap, best_c = ap, candidate
    return best_c, f"selected_inner_{window[0]}-{window[-1]}_ap{best_ap:.4f}"


def run_unit(pop_name: str, rows: list[dict], test_year: int) -> None:
    out_path = OUT_DIR / f"predictions_{pop_name}_{test_year}.csv"
    if out_path.exists():
        print(f"  {pop_name} {test_year}: already done, skipping", flush=True)
        return
    train_rows = [row for row in rows if row["cohort_year"] < test_year]
    test_rows = [row for row in rows if row["cohort_year"] == test_year]
    print(f"  {pop_name} {test_year}: train {len(train_rows)} "
          f"({sum(r['label'] for r in train_rows)} pos) "
          f"test {len(test_rows)} ({sum(r['label'] for r in test_rows)} pos)",
          flush=True)

    vectorizers = fit_vectorizers(train_rows)
    scores = {}
    chosen = {}
    for arm in ARMS:
        started = time.time()
        c_value, provenance = select_c(arm, rows, test_year, vectorizers)
        train_x = build_features(arm, train_rows, train_rows, vectorizers)
        test_x = build_features(arm, train_rows, test_rows, vectorizers)
        model = LogisticRegression(**{**MODEL_KWARGS, "C": c_value})
        model.fit(train_x, np.array([row["label"] for row in train_rows]))
        scores[arm] = model.predict_proba(test_x)[:, 1]
        chosen[arm] = (c_value, provenance)
        print(f"      {arm}: C={c_value} ({provenance}) "
              f"[{time.time() - started:.0f}s]", flush=True)

    partial = out_path.with_suffix(".part")
    with partial.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["adsh", "cik", "cohort_year", "label"]
                        + [f"score_{arm}" for arm in ARMS])
        for index, row in enumerate(test_rows):
            writer.writerow([row["adsh"], row["cik"], row["cohort_year"],
                             row["label"]]
                            + [scores[arm][index] for arm in ARMS])
    partial.replace(out_path)

    with (OUT_DIR / "selected_c.csv").open("a", newline="") as handle:
        writer = csv.writer(handle)
        for arm in ARMS:
            writer.writerow([pop_name, test_year, arm, chosen[arm][0],
                             chosen[arm][1]])
    print(f"    wrote {out_path}", flush=True)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    header = OUT_DIR / "selected_c.csv"
    if not header.exists():
        with header.open("w", newline="") as handle:
            csv.writer(handle).writerow(
                ["population", "cohort_year", "arm", "selected_C", "provenance"])

    panel = load_panel()
    only_pop = None
    if "--population" in sys.argv:
        only_pop = sys.argv[sys.argv.index("--population") + 1]
    only_cohort = None
    if "--cohort" in sys.argv:
        only_cohort = int(sys.argv[sys.argv.index("--cohort") + 1])

    for pop_name in ("B", "A", "DUP"):
        if only_pop and pop_name != only_pop:
            continue
        rows = population(pop_name, panel)
        print(f"\npopulation {pop_name}: {len(rows)} observations, "
              f"{sum(r['label'] for r in rows)} positives", flush=True)
        for test_year in COHORTS:
            if only_cohort and test_year != only_cohort:
                continue
            run_unit(pop_name, rows, test_year)
    print("\nBENCHMARK_UNITS_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
