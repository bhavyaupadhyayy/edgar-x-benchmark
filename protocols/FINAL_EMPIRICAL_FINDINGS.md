# EDGAR-X — Final Empirical Findings

**Date:** 2026-09-22
**Status:** the empirical study is frozen. No further experiments.

This is the complete empirical story, from benchmark construction through the
contamination audit to the strict point-in-time benchmark. Each section points to
its own frozen result document.

---

## 1. Benchmark construction

**A strict point-in-time reconstruction of the SEC information set for predicting
corporate bankruptcy within 365 days.**

The observational unit is one Form 10-K, identified by CIK, evaluated against
whether that registrant filed an initial US Chapter 7 or Chapter 11 petition
within 365 days of the filing's **EDGAR acceptance timestamp**. Every convention
is fixed against the clock: acceptance time rather than filing date; as-filed
DERA financial facts rather than restated ones; historical SIC as filed rather
than a present-day code; FIRE (6000–6799) excluded on the as-filed value;
unknown SIC as its own excluded state; the actual petition date as event time,
never the 8-K disclosure date.

**Scale.** 3,010 assembled bankruptcy events from 3,786 Item 1.03 filings;
**59,500 eligible 10-K observations across 2012–2024 carrying 437 positives**
(prevalence 0.73%); 59,499 primary documents retrieved with zero failures and
zero SHA-256 mismatches.

Label quality was audited on a 188-case untouched holdout drawn at both event and
CIK level, with pre-registered strata and frozen seeds
(`FINAL_VALIDATION_PROTOCOL.md`). Adjudication of the 2012–2024 mapped positives
returned **93/95 confirmed**, 0.9789 unweighted with Wilson 95% CI
[0.9265, 0.9942] (`FINAL_VALIDATION_REPORT.md`).

**Critical caveat carried into every downstream claim:** that adjudication was
performed by a **blinded AI adjudicator, not independent human ground truth**,
and the adjudicating model had developed the classifier it reviewed. All
validation numbers are **classifier-to-AI-adjudicator agreement estimates**
(`FINAL_VALIDATION_PROTOCOL.md` Amendment 2).

## 2. Contamination findings

Four channels were pre-registered, measured and closed
(`CONTAMINATION_FINDINGS_FREEZE.md`). Effects were treated as signed throughout.

### Later / restated financials — no support for the pre-registered hypothesis

Preferring restated facts over as-filed ones did **not** inflate average
precision. The pooled effect was **negative**: ΔAP −0.0025, **−10.49% relative**,
95% CI [−0.0152, +0.0010]. Against the pre-registered rule (MDE 24–33% relative,
power 0.25–0.43 at +15%), the verdict was **KILL**.

**Evidence consistent with a mechanism** for why later-restated financials do not
inflate bankruptcy-prediction performance: **failed registrants often stop
filing, so later revisions disproportionately affect surviving firms.** Restated
values differ for 14.8–36.1% of positives against 24.6–57.8% of negatives, and
under contamination the positives' mean rank *falls*. This is consistent with the
proposed mechanism rather than a demonstration of it. (`GATE2A_RESULT.md`)

### Present-day-survivor universe — major benchmark composition distortion

Restricting to registrants still filing in 2024 removes **35.6% of observations
and 77.7% of positives**, and cuts prevalence from 0.00580 to 0.00201, a **65.4%
reduction**. This is a **composition** problem of large magnitude, not a subtle
scoring problem, and it is reported as counts rather than as a powered AP effect:
the paired estimand retains only 76 positives (projected MDE 51–70%).

Two precision requirements attach: the mechanism is specifically *a
present-day-survivor universe defined by filing activity in 2024*, not
survivorship in general; and the filtering is strongest in early cohorts and
mechanically zero in 2024, so part of the magnitude is elapsed time rather than
firm mortality.

### SIC-vintage contamination — insufficient positive exposure to model

Operationally real — 4,248 observations (7.2%) carry a SIC differing from the
registrant's present-day code, 1,074 CIKs affected, 516 observations would leave
the universe under today's SIC — but **only 2 positives are affected**, and 1 by a
FIRE flip. **KILL BEFORE MODELING.** Preserved as an exposure-audit result about
statistical reach, not about whether SIC vintage is a real data-management
concern.

### Random versus rolling evaluation — heterogeneous protocol sensitivity, not stable leakage

Across 12 cohorts: 8/12 positive, event-weighted **+2.6%** relative, 95% CI
[−0.0036, +0.0084], and aggregate estimators disagreeing by a factor of six
(+2.6% event-weighted to +16.2% pooled). 2024 alone moves the aggregate by 7.2
percentage points.

Two mechanisms are **not supported as dominant**, neither claimed to be
universally excluded:

- **Same-CIK overlap.** The pre-declared CIK-grouped diagnostic drove same-CIK
  training overlap from 79.6% to 0% and left the effect marginally *larger*
  (+4.17% grouped against +2.59%), sign preserved in 11/12. Strong evidence
  against this mechanism.
- **Future-population exposure.** With training volume and positive count held
  exactly fixed over 100 frozen draws per cohort, the cohort median effect fell
  from **+11.87% to +0.04%**, the sign split became 6 positive / 5 negative /
  1 exactly zero, and the effect did not track future exposure (Spearman
  **+0.175**). The 2024 structural control returned **exactly 0** with zero
  variance.

Residual differences are best described as **cohort-specific training-composition
sensitivity**: *which* observations train the model matters more than *when* they
are from. (`GATE2B_CHANNEL3_RESULT.md`, `GATE2C_RESULT.md`)

### What the contamination programme established

No stable, powered performance-inflation effect from any single contaminated
convention this panel could measure. At 341–437 positives the panel cannot
resolve contamination effects at the ±10% relative scale — itself a
methodological finding about the feasibility the field's leakage claims require.

## 3. Main benchmark finding

**Filing text consistently and substantially outperforms financial ratios under
strict temporal evaluation.**

Event-weighted AP rises from **0.0425** (ratios) to **0.1301** (text), a
**ΔAP of +0.0876** and **+206% relative**, positive in **12 of 12 cohorts**, with
eight of twelve bootstrap intervals excluding zero. The conclusion survives both
mandatory sensitivities: **+199%, 12/0** with all validation CIKs removed, and
**+219%, 12/0** with byte-identical documents removed.

It is also robust to cohort deletion: leave-one-cohort-out moves the
event-weighted ΔAP only between +0.0588 and +0.0979. **2020 is the single
influential cohort**, and even removing it leaves a large positive effect.

Operationally, at a 25-filing review budget precision rises from 0.067 to 0.193
and lift from 6.9× to 20.6×; at 100 filings recall rises from 0.123 to 0.324.
These are **ranking results, not deployment claims**.

## 4. Multimodal finding

**Ratios + text strongly beat ratios, but ratios provide only modest and
inconsistent incremental value beyond text.**

C−A is positive in **12/12** cohorts, event-weighted AP **0.1447**, **+240%**
over ratios alone. But C−B is only **+0.0145 event-weighted (+11.2%)**.
**C−B is positive in 10/12 cohorts. Four cohort intervals exclude zero: three
positively** (2017, 2022, 2024) **and 2020 negatively** (−0.1121,
[−0.2037, −0.0195], P=0.008).

**Text carries nearly all the signal. The combination should not be described as
uniformly superior to text alone.** (`GATE4_FINAL_BENCHMARK_RESULT.md`)

## 5. Standing caveats

1. **Validation is AI adjudication, not human ground truth**, and the adjudicator
   was not independent of the classifier. Correlated error biases agreement
   upward by an unknown amount.
2. **Calibration is not claimed.** `class_weight="balanced"` changes the
   probability scale, most severely for Arm A. AP, ROC-AUC and review-budget
   metrics are the ranking-oriented comparisons; Brier, calibration intercept and
   slope characterise raw frozen logistic outputs only. No recalibration was run.
3. **Regularisation.** The temporal selection procedure frequently preferred the
   weakest regularisation in the frozen grid (`C = 10` in 8 of the final 10
   cohorts for text and combined arms). This is not a claim that `C = 10` is
   globally optimal, and the grid was not expanded.
4. **Sparse positives.** 2021 carries 5 positives; its per-cohort figures are
   individually near-meaningless and inflate mean and median views.
5. **Frozen extractor limitation.** 179 Item 1A sections (0.30% of the corpus,
   **0 positives**) are recoverable in principle and deliberately left missing.
6. **Two known label errors** survive in the benchmark — the CCAA and
   same-name-subsidiary cases identified during validation — deliberately
   uncorrected so the holdout was not converted to development data.

## 6. Frozen result documents

| document | scope |
|---|---|
| `FINAL_VALIDATION_PROTOCOL.md` / `FINAL_VALIDATION_REPORT.md` | label validation and its AI-adjudication deviation |
| `GATE2A_RESULT.md` | restatement channel (KILL) |
| `GATE2B_PROTOCOL.md` | three further channels, pre-registered |
| `GATE2B_CHANNEL3_RESULT.md` | temporal evaluation channel |
| `GATE2C_RESULT.md` | matched-volume mechanism diagnostic |
| `CONTAMINATION_FINDINGS_FREEZE.md` | all four channels closed |
| `GATE3_TEXT_CORPUS_RESULT.md` | retrieval and extraction |
| `GATE4_FINAL_BENCHMARK_RESULT.md` | the benchmark |

---

## Erratum — 2026-09-22

**Prose transcription correction only. No interval value, prediction, bootstrap
output, aggregate, sign count or headline result is modified.**

**B − A interval count.** Section 3 originally stated "nine of twelve bootstrap
intervals excluding zero" for the text-over-ratios contrast. The authoritative
per-cohort intervals in `gate4_release/cohort_metrics.csv` imply **eight of
twelve**: 2014, 2015, 2016, 2017, 2018, 2020, 2021 and 2023 exclude zero; 2013,
2019, 2022 and 2024 include it. This is the same correction already recorded in
the `GATE4_FINAL_BENCHMARK_RESULT.md` erratum (commit
`377d57bead56053786ef7d062bc43a3ebaea5f57`), which corrected that document's
tally but left this one unchanged.

The headline is unaffected: the contrast remains positive in 12 of 12 cohorts
with an event-weighted ΔAP of +0.0876 (+206% relative).
