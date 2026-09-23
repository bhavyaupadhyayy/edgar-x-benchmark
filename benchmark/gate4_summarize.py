"""Summarise the frozen benchmark. Reads predictions only; fits no benchmark model.

Aggregation is fixed by protocol and reported as a set, never one number:
cohort median, cohort mean, event-weighted, and pooled observation-level
(explicitly labelled and not the sole headline), plus sign counts.

    python3 gate4_summarize.py [--population B|A|DUP]
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

OUT_DIR = Path("outputs/gate4")
COHORTS = tuple(range(2013, 2025))
ARMS = ("A_ratios", "B_text", "C_combined")
CONTRASTS = (("B_text", "A_ratios"), ("C_combined", "A_ratios"),
             ("C_combined", "B_text"))
BUDGETS = (25, 50, 100, 250)
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20260916


def load(pop: str, year: int):
    path = OUT_DIR / f"predictions_{pop}_{year}.csv"
    if not path.exists():
        return None
    rows = list(csv.DictReader(path.open()))
    labels = np.array([int(r["label"]) for r in rows])
    clusters = [int(r["cik"]) for r in rows]
    scores = {arm: np.array([float(r[f"score_{arm}"]) for r in rows])
              for arm in ARMS}
    return labels, scores, clusters


def calibration(labels, score):
    eps = 1e-9
    p = np.clip(score, eps, 1 - eps)
    logit = np.log(p / (1 - p)).reshape(-1, 1)
    model = LogisticRegression(C=1e9, solver="lbfgs", max_iter=5000)
    model.fit(logit, labels)
    return float(model.intercept_[0]), float(model.coef_[0][0])


def budget_metrics(labels, score):
    order = np.argsort(-score, kind="stable")
    ranked = labels[order]
    positives = int(labels.sum())
    prevalence = positives / len(labels)
    out = {}
    budgets = list(BUDGETS) + [max(1, int(round(0.01 * len(labels))))]
    names = [str(b) for b in BUDGETS] + ["top1pct"]
    for budget, name in zip(budgets, names):
        hits = int(ranked[:budget].sum())
        precision = hits / budget
        out[f"precision_at_{name}"] = precision
        out[f"recall_at_{name}"] = hits / positives if positives else float("nan")
        out[f"lift_at_{name}"] = precision / prevalence if prevalence else float("nan")
    return out


def cluster_bootstrap(labels, score_a, score_b, clusters, seed=BOOTSTRAP_SEED):
    rng = np.random.default_rng(seed)
    index_of = defaultdict(list)
    for position, cluster in enumerate(clusters):
        index_of[cluster].append(position)
    keys = list(index_of)
    deltas, rels = [], []
    for _ in range(BOOTSTRAP_REPLICATES):
        picked = rng.integers(0, len(keys), size=len(keys))
        rows = []
        for position in picked:
            rows.extend(index_of[keys[position]])
        y = labels[rows]
        if y.sum() == 0 or y.sum() == len(y):
            continue
        ap_a = average_precision_score(y, score_a[rows])
        ap_b = average_precision_score(y, score_b[rows])
        deltas.append(ap_b - ap_a)
        if ap_a > 0:
            rels.append((ap_b - ap_a) / ap_a)
    return np.array(deltas), np.array(rels)


def summarise_population(pop: str) -> dict:
    per_cohort = {}
    for year in COHORTS:
        got = load(pop, year)
        if got is None:
            continue
        labels, scores, clusters = got
        entry = {"n": len(labels), "positives": int(labels.sum()),
                 "clusters": clusters, "labels": labels, "scores": scores}
        for arm in ARMS:
            entry[f"ap_{arm}"] = average_precision_score(labels, scores[arm])
            entry[f"auc_{arm}"] = roc_auc_score(labels, scores[arm])
            entry[f"brier_{arm}"] = brier_score_loss(labels, scores[arm])
            a, b = calibration(labels, scores[arm])
            entry[f"cal_intercept_{arm}"] = a
            entry[f"cal_slope_{arm}"] = b
            entry.update({f"{k}_{arm}": v
                          for k, v in budget_metrics(labels, scores[arm]).items()})
        for high, low in CONTRASTS:
            key = f"{high}_vs_{low}"
            delta = entry[f"ap_{high}"] - entry[f"ap_{low}"]
            entry[f"delta_{key}"] = delta
            entry[f"relative_{key}"] = (delta / entry[f"ap_{low}"]
                                        if entry[f"ap_{low}"] > 0 else float("nan"))
            deltas, rels = cluster_bootstrap(labels, scores[low], scores[high],
                                             clusters)
            entry[f"boot_mean_{key}"] = float(deltas.mean())
            entry[f"boot_lo_{key}"] = float(np.percentile(deltas, 2.5))
            entry[f"boot_hi_{key}"] = float(np.percentile(deltas, 97.5))
            entry[f"boot_p_gt0_{key}"] = float((deltas > 0).mean())
            entry[f"boot_rel_mean_{key}"] = (float(rels.mean()) if len(rels)
                                             else float("nan"))
        per_cohort[year] = entry
    return per_cohort


def aggregate(per_cohort: dict, field: str) -> dict:
    years = sorted(per_cohort)
    values = np.array([per_cohort[y][field] for y in years])
    weights = np.array([per_cohort[y]["positives"] for y in years], dtype=float)
    weights = weights / weights.sum()
    return {
        "cohort_median": float(np.median(values)),
        "cohort_mean": float(values.mean()),
        "event_weighted": float(np.dot(weights, values)),
        "cohorts_positive": int((values > 0).sum()),
        "cohorts_negative": int((values < 0).sum()),
    }


def pooled(per_cohort: dict, arm: str) -> dict:
    labels = np.concatenate([per_cohort[y]["labels"] for y in sorted(per_cohort)])
    score = np.concatenate([per_cohort[y]["scores"][arm]
                            for y in sorted(per_cohort)])
    return {"ap": average_precision_score(labels, score),
            "auc": roc_auc_score(labels, score)}


def report(pop: str, per_cohort: dict) -> dict:
    years = sorted(per_cohort)
    print("=" * 100)
    print(f"POPULATION {pop} — {len(years)} cohorts")
    print("=" * 100)
    print(f"{'year':>5}{'n':>7}{'pos':>5}"
          f"{'AP A':>9}{'AP B':>9}{'AP C':>9}"
          f"{'AUC A':>8}{'AUC B':>8}{'AUC C':>8}"
          f"{'B-A':>9}{'C-A':>9}{'C-B':>9}")
    for year in years:
        e = per_cohort[year]
        print(f"{year:>5}{e['n']:>7}{e['positives']:>5}"
              f"{e['ap_A_ratios']:>9.4f}{e['ap_B_text']:>9.4f}"
              f"{e['ap_C_combined']:>9.4f}"
              f"{e['auc_A_ratios']:>8.4f}{e['auc_B_text']:>8.4f}"
              f"{e['auc_C_combined']:>8.4f}"
              f"{e['delta_B_text_vs_A_ratios']:>+9.4f}"
              f"{e['delta_C_combined_vs_A_ratios']:>+9.4f}"
              f"{e['delta_C_combined_vs_B_text']:>+9.4f}")

    print(f"\n{'arm':<14}{'median AP':>11}{'mean AP':>10}{'evt-wtd AP':>12}"
          f"{'pooled AP':>11}{'pooled AUC':>12}")
    summary = {"population": pop, "cohorts": years, "arms": {}, "contrasts": {}}
    for arm in ARMS:
        agg = aggregate(per_cohort, f"ap_{arm}")
        pl = pooled(per_cohort, arm)
        summary["arms"][arm] = {**agg, "pooled_ap": pl["ap"], "pooled_auc": pl["auc"]}
        print(f"{arm:<14}{agg['cohort_median']:>11.4f}{agg['cohort_mean']:>10.4f}"
              f"{agg['event_weighted']:>12.4f}{pl['ap']:>11.4f}{pl['auc']:>12.4f}")

    print(f"\n{'contrast':<26}{'median':>10}{'mean':>10}{'evt-wtd':>10}"
          f"{'rel evt-wtd':>13}{'+/-':>8}")
    for high, low in CONTRASTS:
        key = f"{high}_vs_{low}"
        agg = aggregate(per_cohort, f"delta_{key}")
        base = aggregate(per_cohort, f"ap_{low}")["event_weighted"]
        rel = agg["event_weighted"] / base if base else float("nan")
        summary["contrasts"][key] = {**agg, "relative_event_weighted": rel}
        print(f"{key:<26}{agg['cohort_median']:>+10.4f}{agg['cohort_mean']:>+10.4f}"
              f"{agg['event_weighted']:>+10.4f}{rel:>+12.2%}"
              f"{agg['cohorts_positive']}/{agg['cohorts_negative']:>3}")

    print(f"\nper-cohort paired bootstrap, 95% intervals "
          f"({BOOTSTRAP_REPLICATES} CIK-cluster replicates, seed {BOOTSTRAP_SEED})")
    for high, low in CONTRASTS:
        key = f"{high}_vs_{low}"
        print(f"  {key}")
        for year in years:
            e = per_cohort[year]
            print(f"    {year}  dAP {e[f'delta_{key}']:+.4f}  "
                  f"rel {e[f'relative_{key}']:+7.1%}  "
                  f"95% CI [{e[f'boot_lo_{key}']:+.4f}, "
                  f"{e[f'boot_hi_{key}']:+.4f}]  "
                  f"P(>0) {e[f'boot_p_gt0_{key}']:.3f}")

    print(f"\ncalibration (raw logistic probabilities, no isotonic)")
    print(f"{'year':>5}" + "".join(f"{'Brier ' + a[0]:>11}" for a in ARMS)
          + "".join(f"{'int ' + a[0]:>9}{'slope ' + a[0]:>11}" for a in ARMS))
    for year in years:
        e = per_cohort[year]
        line = f"{year:>5}"
        for arm in ARMS:
            line += f"{e[f'brier_{arm}']:>11.5f}"
        for arm in ARMS:
            line += f"{e[f'cal_intercept_{arm}']:>9.3f}{e[f'cal_slope_{arm}']:>11.3f}"
        print(line)

    print(f"\nreview-budget metrics, event-weighted across cohorts")
    print(f"{'metric':<22}" + "".join(f"{a:>14}" for a in ARMS))
    weights = np.array([per_cohort[y]["positives"] for y in years], dtype=float)
    weights /= weights.sum()
    for name in [str(b) for b in BUDGETS] + ["top1pct"]:
        for kind in ("precision", "recall", "lift"):
            field = f"{kind}_at_{name}"
            line = f"{kind + '@' + name:<22}"
            for arm in ARMS:
                values = np.array([per_cohort[y][f"{field}_{arm}"] for y in years])
                line += f"{float(np.dot(weights, values)):>14.4f}"
            print(line)
    return summary


def main() -> int:
    only = None
    if "--population" in sys.argv:
        only = sys.argv[sys.argv.index("--population") + 1]
    summaries = {}
    for pop in ("B", "A", "DUP"):
        if only and pop != only:
            continue
        per_cohort = summarise_population(pop)
        if not per_cohort:
            print(f"\npopulation {pop}: no predictions yet")
            continue
        summaries[pop] = report(pop, per_cohort)
        print()
    (OUT_DIR / "benchmark_summary.json").write_text(json.dumps(summaries, indent=2))
    print(f"wrote {OUT_DIR / 'benchmark_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
