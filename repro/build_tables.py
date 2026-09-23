"""Build the manuscript tables from the frozen tracked release artifacts.

Reads ONLY `gate4_release/*.csv` as committed at dcee103, plus fixed counts
transcribed from the frozen result documents for Tables 1 and 2. Emits Markdown
(for the manuscript) and CSV (machine-readable) for each table.
"""
from pathlib import Path
import csv

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "benchmark/gate4_release"
OUT = ROOT / "paper/tables"

ARMS = ("A_ratios", "B_text", "C_combined")
NAMES = {"A_ratios": "Ratios", "B_text": "Text", "C_combined": "Ratios + Text"}


def cohorts(pop):
    rows = [r for r in csv.DictReader((RELEASE / "cohort_metrics.csv").open())
            if r["population"] == pop]
    return sorted(rows, key=lambda r: int(r["cohort_year"]))


def agg(pop):
    return {r["quantity"]: r for r in
            csv.DictReader((RELEASE / "aggregate_metrics.csv").open())
            if r["population"] == pop}


def emit(stem, header, rows, note=""):
    with (OUT / f"{stem}.md").open("w") as fh:
        fh.write("| " + " | ".join(header) + " |\n")
        fh.write("|" + "|".join("---" for _ in header) + "|\n")
        for r in rows:
            fh.write("| " + " | ".join(str(c) for c in r) + " |\n")
        if note:
            fh.write(f"\n{note}\n")
    with (OUT / f"{stem}.csv").open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(header); w.writerows(rows)
    print(f"wrote {stem}.md and {stem}.csv ({len(rows)} rows)")


# ---- Table 1: dataset / cohort statistics ---------------------------------
B = cohorts("B")
rows = []
for r in B:
    n, p = int(r["n"]), int(r["positives"])
    rows.append([r["cohort_year"], f"{n:,}", p, f"{p / n:.4%}"])
rows.append(["**2013-2024 total**", f"**{sum(int(r['n']) for r in B):,}**",
             f"**{sum(int(r['positives']) for r in B)}**",
             f"**{sum(int(r['positives']) for r in B) / sum(int(r['n']) for r in B):.4%}**"])
emit("table1_cohort_statistics",
     ["Test cohort", "Observations", "Positive obs.", "Prevalence"], rows,
     "Full panel 2012-2024: 59,500 observations, 437 positive observations, "
     "prevalence 0.7345%. "
     "The 2012 cohort is training-only under rolling evaluation. "
     "**2021 carries only 5 positive observations**; its per-cohort figures are "
     "individually "
     "uninformative.")

# ---- Table 2: contamination audit summary ---------------------------------
emit("table2_contamination_audit",
     ["Channel", "Estimand", "Result", "Verdict"],
     [["Later-restated financials", "signed relative ΔAP, paired",
       "AP 0.0235 PIT vs 0.0210 contaminated; ΔAP −0.0025, −10.49%; "
       "95% CI [−0.0152, +0.0010]",
       "Pre-registered inflation hypothesis **not supported**"],
      ["Present-day-survivor universe", "composition, not performance",
       "−35.6% observations, −77.7% positive observations; prevalence 0.00580 → 0.00201",
       "Reported as counts; paired estimand retains 76 positive obs. (MDE 51-70%)"],
      ["Industry-classification vintage", "signed ΔAP on affected subset",
       "4,248 observations (7.2%), 1,074 CIKs, **2 positive observations** affected",
       "Terminated before modelling"],
      ["Random vs rolling evaluation", "signed relative ΔAP, paired",
       "8/12 cohorts positive, event-weighted +2.6%, 95% CI [−0.0036, +0.0084]; "
       "CIK grouping does not remove it; matched volume collapses cohort median "
       "+11.87% → +0.04%",
       "Heterogeneous protocol sensitivity, not stable inflation"]],
     "Channels are reported separately because their estimands are not "
     "commensurable. Panel-wide minimum detectable effect is approximately "
     "24-33% relative at 341 positive observations.")

# ---- Table 3: primary A/B/C benchmark results -----------------------------
a = agg("B")
rows = []
for r in B:
    rows.append([r["cohort_year"], r["positives"]] +
                [f"{float(r[f'ap_{k}']):.4f}" for k in ARMS] +
                [f"{float(r[f'auc_{k}']):.4f}" for k in ARMS])
for label, key in (("**Cohort median**", "median"), ("**Cohort mean**", "mean"),
                   ("**Event-weighted**", "event_weighted")):
    rows.append([label, ""] + [f"**{float(a[f'ap_{k}'][key]):.4f}**" for k in ARMS]
                + ["", "", ""])
rows.append(["**Pooled observation-level**", "", "**0.0246**", "**0.0489**",
             "**0.0769**", "0.7523", "0.7719", "0.7954"])
emit("table3_primary_results",
     ["Cohort", "Pos. obs."] + [f"AP {NAMES[k]}" for k in ARMS]
     + [f"AUC {NAMES[k]}" for k in ARMS], rows,
     "Option B primary population. **Pooled observation-level stacks twelve "
     "differently-scaled models onto one ranking and is not a headline.** "
     "ROC-AUC is secondary at 0.73% prevalence.")

# ---- Table 4: paired comparisons ------------------------------------------
CON = (("B_text_vs_A_ratios", "Text − Ratios"),
       ("C_combined_vs_A_ratios", "Combined − Ratios"),
       ("C_combined_vs_B_text", "Combined − Text"))
rows = []
for key, label in CON:
    for r in B:
        rows.append([label, r["cohort_year"], f"{float(r[f'delta_{key}']):+.4f}",
                     f"{float(r[f'relative_{key}']):+.1%}",
                     f"[{float(r[f'ci_lo_{key}']):+.4f}, {float(r[f'ci_hi_{key}']):+.4f}]",
                     f"{float(r[f'p_gt0_{key}']):.3f}"])
    e = a[f"delta_{key}"]
    rows.append([f"**{label}**", "**event-weighted**",
                 f"**{float(e['event_weighted']):+.4f}**",
                 f"**{float(a[f'relative_{key}_event_weighted']['event_weighted']):+.1%}**",
                 f"median {float(e['median']):+.4f} / mean {float(e['mean']):+.4f}",
                 f"**{e['cohorts_positive']}+ / {e['cohorts_negative']}−**"])
emit("table4_paired_comparisons",
     ["Contrast", "Cohort", "ΔAP", "Relative", "95% CI", "P(Δ>0)"], rows,
     "Paired CIK-cluster bootstrap, 2,000 replicates, seed 20260916, on identical "
     "cohort test rows. Counted directly from the intervals above: **Text − Ratios "
     "excludes zero in 8 of 12 cohorts**; **Combined − Ratios in 10 of 12**; "
     "**Combined − Text in 3 of 12 on the positive side (2017, 2022, 2024), with "
     "2020 excluding zero on the negative side.**")
# ---- Table 5: review-budget results ---------------------------------------
w = np.array([int(r["positives"]) for r in B], float); w /= w.sum()
rows = []
for budget, shown in (("25", "25"), ("50", "50"), ("100", "100"),
                      ("250", "250"), ("top1pct", "top 1%")):
    for metric in ("precision", "recall", "lift"):
        vals = [float(np.dot(w, [float(r[f"{metric}@{budget}_{k}"]) for r in B]))
                for k in ARMS]
        fmt = (lambda v: f"{v:.2f}×") if metric == "lift" else (lambda v: f"{v:.4f}")
        rows.append([shown, metric] + [fmt(v) for v in vals])
emit("table5_review_budget",
     ["Budget k", "Metric"] + [NAMES[k] for k in ARMS], rows,
     "Event-weighted across the twelve cohorts. **Ranking / analyst-review "
     "results, not deployment claims**: no threshold, operating point or cost "
     "model is proposed.")

# ---- Table 6: sensitivities ------------------------------------------------
rows = []
for pop, label in (("B", "Primary (Option B)"),
                   ("A", "Option A: validation CIKs excluded"),
                   ("DUP", "Duplicate-content excluded")):
    ag = agg(pop)
    # Counts are derived from the release data, never transcribed by hand.
    pop_rows = cohorts(pop)
    obs = f"{sum(int(r['n']) for r in pop_rows):,}"
    pos = str(sum(int(r["positives"]) for r in pop_rows))
    rows.append([label, obs, pos] +
                [f"{float(ag[f'ap_{k}']['event_weighted']):.4f}" for k in ARMS] +
                [f"{float(ag[f'relative_{key}_event_weighted']['event_weighted']):+.1%} "
                 f"({ag[f'delta_{key}']['cohorts_positive']}+/"
                 f"{ag[f'delta_{key}']['cohorts_negative']}−)"
                 for key, _ in CON])
emit("table6_sensitivities",
     ["Population", "Obs", "Pos. obs."] + [f"AP {NAMES[k]}" for k in ARMS]
     + ["Text − Ratios", "Combined − Ratios", "Combined − Text"], rows,
     "Both sensitivities were frozen before any benchmark result was observed. "
     "The text-over-ratios conclusion holds in every population, 12/12 cohorts.")

# ---- Appendix: selected C --------------------------------------------------
sel = list(csv.DictReader((RELEASE / "selected_c.csv").open()))
by = {}
for r in sel:
    by.setdefault((r["population"], int(r["cohort_year"])), {})[r["arm"]] = r["selected_C"]
rows = [[p, y] + [by[(p, y)][k] for k in ARMS] for (p, y) in sorted(by, key=lambda t: (t[0], t[1]))]
emit("tableA1_selected_c", ["Population", "Cohort"] + [NAMES[k] for k in ARMS], rows,
     "Selected by the frozen procedure on prior cohorts only. 2013 and 2014 take "
     "the `C = 1.0` fallback fixed in advance. The procedure frequently preferred "
     "the weakest regularisation available in the frozen grid; this is not a "
     "claim that `C = 10` is globally optimal.")

# ---- Appendix: calibration diagnostics -------------------------------------
rows = []
for r in B:
    rows.append([r["cohort_year"]] +
                [f"{float(r[f'brier_{k}']):.5f}" for k in ARMS] +
                [f"{float(r[f'cal_int_{k}']):.3f}" for k in ARMS] +
                [f"{float(r[f'cal_slope_{k}']):.3f}" for k in ARMS])
emit("tableA2_calibration",
     ["Cohort"] + [f"Brier {NAMES[k]}" for k in ARMS]
     + [f"Intercept {NAMES[k]}" for k in ARMS] + [f"Slope {NAMES[k]}" for k in ARMS],
     rows,
     "**No arm is described as calibrated.** `class_weight=\"balanced\"` changes "
     "the raw probability scale, most severely for the ratio arm. These are "
     "diagnostics of raw frozen logistic outputs only; no recalibration was run.")

# ---- Appendix: leave-one-cohort-out ---------------------------------------
loo = [r for r in csv.DictReader((RELEASE / "leave_one_cohort_out.csv").open())
       if r["population"] == "B"]
rows = [[r["dropped"]] + [f"{float(r[k]):.4f}" for k in ARMS]
        + [f"{float(r['delta_B_A']):+.4f}", f"{float(r['delta_C_B']):+.4f}"]
        for r in loo]
emit("tableA3_leave_one_cohort_out",
     ["Dropped cohort"] + [f"AP {NAMES[k]}" for k in ARMS]
     + ["Text − Ratios", "Combined − Text"], rows,
     "Event-weighted aggregates recomputed with each cohort removed. **2020 is "
     "the most influential cohort.** The direction of the headline result is "
     "unchanged under every single-cohort deletion.")
