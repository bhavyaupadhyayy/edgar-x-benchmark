# Gate 2A Result — restatement / later-facts contamination

**Date:** 2026-09-16
**Status:** FROZEN. **Decision: KILL** for the restatement-driven AP-inflation hypothesis.
**Code:** `gate2_extract.py`, `gate2_panel.py`, `gate2_pilot.py`, `gate2_ablation.py`,
`gate2_diagnose.py`, `gate2_power_empirical.py` (commits `f8e1d32`, `ae06613`)

---

## 1. What was tested

Whether evaluating a bankruptcy-prediction model under *restated* financial
facts inflates measured performance relative to strict point-in-time facts.

Contamination was applied on three documented channels and no others:

1. **Restated facts** — a fact for fiscal period P may come from a submission
   filed after the observation date; latest filed wins. This is the documented
   behaviour of `EdgarClient.get_fundamentals_history` (PIT contract §2).
2. **Present-day SIC** instead of the SIC as filed.
3. **Pooled medians** — industry and imputation medians computed over the whole
   panel, including the test cohort and later years, instead of the training
   fold only.

Survivorship was deliberately excluded: it changes panel membership, which
would break the pairing the paired bootstrap depends on. It is Gate 2B's
channel 1.

Financial ratios only. No text, LLM, macro or multimodal features. One fixed
logistic model, identical hyperparameters in both arms, no search of any kind.

## 2. Pilot cohorts

Selected mechanically from the frozen 2012–2024 positive-observation vector
`(29,16,32,39,46,28,28,45,48,5,29,61,44)`, considering only cohorts with at
least 25 positives, **before any model was fitted**:

| role | year | positives | selection |
|---|---|---|---|
| low-event | **2017** | 28 | minimum among eligible — **tied with 2018 (also 28)**, broken by earliest year |
| median-event | **2015** | 39 | median of 11 eligible cohorts (6th of sorted counts) |
| high-event | **2023** | 61 | unique maximum |

2013 (16) and 2021 (5) were ineligible. The 2017/2018 tie is recorded because
the stated rule does not break it; 2018 is an equally valid low-event cohort.

## 3. Strict validation-CIK exclusion rerun

All 188 CIKs in the frozen final-validation sample were removed from the panel
once, before any split, so training rows, test rows and both arms lose the same
CIKs. Panel 59,500 → 58,789 rows; positives 437 → 341. Verified: zero
validation CIKs remain in any strict test set, each strict test set is a subset
of the original, and both arms stay paired on identical rows.

| | 2017 low | 2015 median | 2023 high | pooled |
|---|---|---|---|---|
| observations before → after | 4,492 → 4,439 | 4,990 → 4,922 | 4,456 → 4,415 | 13,938 → 13,776 |
| positives before → after | 27 → 21 | 36 → 25 | 61 → 48 | 124 → 94 |
| **AP strict PIT** | 0.0146 → **0.0103** | 0.0163 → **0.0140** | 0.0482 → **0.0342** | 0.0316 → **0.0235** |
| **AP contaminated** | 0.0143 → **0.0101** | 0.0168 → **0.0146** | 0.0444 → **0.0291** | 0.0298 → **0.0210** |
| **signed ΔAP** | −0.0002 → **−0.0002** | +0.0005 → **+0.0007** | −0.0039 → **−0.0051** | −0.0018 → **−0.0025** |
| **relative change** | −1.64% → **−2.29%** | +3.09% → **+4.76%** | −8.00% → **−14.81%** | −5.71% → **−10.49%** |
| ROC-AUC PIT / contaminated | .694/.690 → **.712/.701** | .726/.724 → **.781/.784** | .720/.707 → **.687/.676** | — |
| **bootstrap ΔAP 95% CI** | [−.0015, +.0008] | [−.0019, +.0049] | [−.0297, +.0014] | **[−.0152, +.0010]** |
| P(ΔAP > 0) | 0.281 | 0.608 | 0.077 | **0.123** |
| **score correlation** (Pearson) | 0.9405 | 0.9326 | 0.9594 | — |
| **bootstrap corr(AP_A, AP_B)** | 0.9915 | 0.9367 | 0.9240 | **0.9226** |
| bootstrap covariance | 2.02e−5 | 2.16e−5 | 2.38e−4 | 6.36e−5 |
| variance reduction from pairing | 0.991 | 0.934 | 0.877 | 0.878 |

Exclusion removed 24% of positives, lowering AP levels and widening intervals.
It did not reverse the sign or create an effect: the pooled point estimate stays
negative and roughly doubles in magnitude.

## 4. Why the effect is negative — mechanism, not noise

**Contamination barely reaches the positive class.** Share of observations whose
raw ratios differ between arms:

| cohort | positives | negatives |
|---|---|---|
| 2015 | 36.1% | 56.5% |
| 2017 | 14.8% | 57.8% |
| 2023 | 14.8% | 24.6% |

A registrant that files Chapter 7/11 stops filing, so nobody ever restates its
last 10-K. The restatement channel therefore acts mostly on survivors. Mean
rank shift under contamination confirms the direction: positives move **down**
(−20.6, −8.0, −54.0 places in 2017/2015/2023) while negatives barely move.
Restatement makes the bankrupt firms look marginally safer, so AP degrades.

Channel ablation (base run): look-ahead SIC + pooled medians contribute +0.10%
to +2.38%; restated values alone drive −12.64% in 2023. The restated-value
channel is the whole effect.

One time-truncation artifact worth carrying forward: the channel weakens
mechanically in recent cohorts because less time has elapsed for restatements to
accumulate (negatives restated: 56.6% in 2018, 10.4% in 2024).

## 5. Gate 2 on measured inputs

Every design-stage assumption was replaced by a pilot measurement.

| input | assumed | measured |
|---|---|---|
| AP under strict PIT | 0.15 | **0.0103 – 0.0342** (pooled 0.0235) |
| score correlation | 0.90 (grid to 0.95) | **0.92 – 0.99** (pooled 0.9226) |
| **firm ICC** | 0.30 | **0.52** (PIT linear predictor, repeat filers) |
| fold positive counts | 25/40/60 × cycle | **(24,13,27,25,37,21,21,33,37,4,19,48,32)** = 341 |
| prevalence | 0.01 | **0.0058** |
| duplicate positive rate | 0.0 | **0.0235** |
| reference effect | +0.05 AP / +15% | **−10.49% relative observed** |

Standard errors simulated under the null; power evaluated at signed alternatives.

At the pooled measured correlation (0.92), measured ICC (0.52), central
AP_PIT (0.0235):

- SE on relative inflation **11.79%** → **empirical MDE 33.02%**
- **power at +10% relative: 0.136**
- **power at +15% relative: 0.247**
- **power at the observed −10.49%: 0.145**

Across the measured correlation range 0.92–0.95: **MDE 24–33% relative**, power
at +15% **0.25–0.43**, power at +10% **0.14–0.22**. Only at ρ = 0.99 — above the
pooled value, achieved in one cohort — does power at +15% reach 0.74–0.81.

## 6. Decision

Against the pre-registered rule (GO if useful at ρ=0.70; CONDITIONAL if only at
ρ≥0.90; KILL if not useful even at ρ=0.95), power at +15% under ρ=0.95 is
0.345–0.426, roughly half the 0.80 target.

**KILL for restatement-driven AP inflation.**

The old grid's apparent GO came from powering a **+0.05 absolute** AP effect at
an assumed AP_PIT of 0.15. At the measured AP_PIT of 0.0235 that alternative is
a **+213% relative** inflation — not a plausible effect size. The apparent power
was an artifact of an AP assumption ten times too high.

## 7. Statements required for the record

- **The observed effect is negative, not positive.** Pooled ΔAP after strict
  exclusion is −0.0025 (−10.49% relative). The hypothesis was that contamination
  inflates AP; the data show mild degradation.
- **No classifier or contamination-rule changes were made in response.** Gate 1
  labels, the frozen AI validation, the model family, the feature set, the
  tuning procedure (there is none) and the contamination construction are all
  unchanged from before the result was seen. Nothing was tuned to rescue it.
- **No full 2012–2024 experiment was run for this channel.** Only the three
  pre-selected pilot cohorts were evaluated, in both the base and
  strict-exclusion runs.
- **Restatement contamination remains an informative negative/null channel in
  EDGAR-X.** The result stays in the paper as a real finding: for a
  financial-ratio bankruptcy model, preferring restated facts over as-filed ones
  does not inflate average precision, and the mechanism is identifiable —
  failed registrants stop filing, so their facts are never restated, and the
  contamination lands almost entirely on survivors.

## 8. Artifacts

Generated outputs under `outputs/gate2/` (untracked by design): `panel.jsonl`,
`predictions_{2015,2017,2023}{,_strict}.csv`, `bootstrap_*.npz` (2,000 paired
draws each), `pilot_results.csv`, `pilot_results_strict.csv`,
`ablation_results.csv`, `power_grid_empirical.csv`.
