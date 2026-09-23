# Gate 2C Result — matched-volume mechanism diagnostic

**Date:** 2026-09-20
**Status:** FROZEN at commit `63efd1b`. No further post-hoc experiments for Channel 3.
**Nature:** post-hoc mechanism diagnostic motivated by the completed Channel 3
experiment. **Not pre-registered confirmation, and never to be presented as such.**
**Code:** `gate2c_matched_volume.py`; protocol `GATE2C_MATCHED_VOLUME_PROTOCOL.md`

---

## 1. Question and design

> When training-set size and positive count are held fixed, does allowing
> future-period observations into training still change bankruptcy-prediction
> performance?

**Arm A** is the frozen strict-temporal setup from Channel 3: for test cohort Y,
train on all observations with cohort year < Y. **Arm B** tests the identical
rows but draws its training set from all eligible non-test observations, future
years included, matched exactly on total training observations and positive
count — and therefore on negatives too.

All 12 rolling-testable cohorts, 2013–2024. Strict validation-CIK exclusion,
financial ratios only, one fixed logistic model, unchanged preprocessing.

## 2. Exact Arm-A equivalence

Preprocessing was re-implemented vectorised for speed, then proved equivalent
before any Arm-B number was produced. Every cohort's recomputed Arm-A average
precision reproduced the frozen Channel 3 value to **0.00e+00** — bit-identical,
not merely within the 1e-9 tolerance — and the run aborts otherwise.

| year | recomputed AP | frozen AP | \|gap\| |
|---|---|---|---|
| 2013 | 0.009478704633 | 0.009478704633 | 0.00e+00 |
| 2014 | 0.016007755364 | 0.016007755364 | 0.00e+00 |
| 2015 | 0.013958809219 | 0.013958809219 | 0.00e+00 |
| 2016 | 0.054048155813 | 0.054048155813 | 0.00e+00 |
| 2017 | 0.010295734082 | 0.010295734082 | 0.00e+00 |
| 2018 | 0.024793964200 | 0.024793964200 | 0.00e+00 |
| 2019 | 0.075741686454 | 0.075741686454 | 0.00e+00 |
| 2020 | 0.032909407526 | 0.032909407526 | 0.00e+00 |
| 2021 | 0.035136034511 | 0.035136034511 | 0.00e+00 |
| 2022 | 0.012762992259 | 0.012762992259 | 0.00e+00 |
| 2023 | 0.034191570476 | 0.034191570476 | 0.00e+00 |
| 2024 | 0.050133162159 | 0.050133162159 | 0.00e+00 |

## 3. Sampling, frozen before results

**100 matched draws** per cohort. Seed for cohort Y draw d:
`20260921 + 1000 * (Y - 2013) + d`, declared in the protocol before any Arm-B
result was inspected. Positives and negatives drawn uniformly without
replacement from their non-test pools; **which** future rows are selected is
never optimised. Every draw asserts the exact Arm-A training N and positive
count. **No draw was discarded for any reason.**

## 4. Cohort results

Arm-A and Arm-B training N and positive counts are equal by construction in
every cohort.

| year | train N | train pos | % Arm-B rows after cohort | AP strict | AP matched mean | median | sd | ΔAP mean | rel ΔAP mean | rel median | 95% interval across draws | draws Δ>0 | AUC strict → matched |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2013 | 5,076 | 24 | 90.5% | 0.0095 | 0.0091 | 0.0093 | 0.0024 | −0.0003 | −3.6% | −1.6% | [−0.0049, +0.0037] | 48% | .793 → .672 |
| 2014 | 10,056 | 37 | 81.3% | 0.0160 | 0.0215 | 0.0196 | 0.0090 | +0.0055 | +34.3% | +22.7% | [−0.0058, +0.0315] | 73% | .714 → .693 |
| 2015 | 15,045 | 64 | 72.0% | 0.0140 | 0.0140 | 0.0139 | 0.0018 | +0.0000 | +0.1% | −0.8% | [−0.0032, +0.0037] | 46% | .781 → .767 |
| 2016 | 19,967 | 89 | 63.2% | 0.0540 | 0.0447 | 0.0435 | 0.0083 | −0.0093 | −17.3% | −19.5% | [−0.0244, +0.0079] | 14% | .799 → .786 |
| 2017 | 24,455 | 126 | 55.0% | 0.0103 | 0.0139 | 0.0137 | 0.0017 | +0.0036 | +35.4% | +33.5% | [+0.0009, +0.0068] | **100%** | .712 → .732 |
| 2018 | 28,894 | 147 | 47.0% | 0.0248 | 0.0304 | 0.0293 | 0.0048 | +0.0056 | +22.6% | +18.1% | [−0.0009, +0.0176] | 95% | .854 → .845 |
| 2019 | 33,191 | 168 | 39.2% | 0.0757 | 0.0938 | 0.0952 | 0.0170 | +0.0181 | +23.9% | +25.8% | [−0.0068, +0.0463] | 82% | .765 → .770 |
| 2020 | 37,376 | 201 | 31.7% | 0.0329 | 0.0292 | 0.0290 | 0.0017 | −0.0037 | −11.2% | −12.0% | [−0.0065, +0.0008] | 5% | .815 → .799 |
| 2021 | 41,445 | 238 | 24.1% | 0.0351 | 0.0281 | 0.0256 | 0.0071 | −0.0070 | −19.9% | −27.0% | [−0.0141, +0.0127] | 14% | .891 → .878 |
| 2022 | 45,650 | 242 | 15.9% | 0.0128 | 0.0126 | 0.0126 | 0.0011 | −0.0002 | −1.5% | −1.2% | [−0.0025, +0.0021] | 48% | .710 → .725 |
| 2023 | 50,175 | 261 | 7.7% | 0.0342 | 0.0357 | 0.0367 | 0.0024 | +0.0016 | +4.5% | +7.5% | [−0.0029, +0.0048] | 63% | .687 → .692 |
| **2024** | 54,590 | 309 | **0.0%** | 0.0501 | 0.0501 | 0.0501 | **0.0000** | **+0.0000** | **+0.00%** | +0.00% | [+0.0000, +0.0000] | 0% | .709 → .709 |

## 5. The 2024 structural control

For 2024 the non-test pool is *exactly* the Arm-A training set — 54,590
observations and 309 positives either way — so the matched-volume procedure is
forced to reproduce Arm A. It did: **ΔAP exactly 0.0000 with zero variance
across all 100 draws.** The procedure therefore introduces no sampling or
composition artifact of its own.

This also reprices Channel 3's single most influential cohort. 2024's Channel 3
effect of **−39.7%** becomes **exactly 0.00%** once training volume is matched,
because Arm A had 309 training positives against random K-fold's ≈273. That
cohort's apparent effect was the volume asymmetry, not anything temporal.

## 6. Aggregate statistics, before and after matching

| estimator | Channel 3 | Gate 2C matched | change |
|---|---|---|---|
| cohort **median** relative | **+11.87%** | **+0.04%** | −11.83pp |
| cohort **mean** relative | +12.14% | **+5.61%** | −6.53pp |
| **event-weighted** relative | +2.59% | **+4.51%** | +1.92pp |
| cohort mean absolute ΔAP | +0.00091 | +0.00115 | +0.00024 |
| **sign split** | 8 pos / 4 neg / 0 zero | **6 pos / 5 neg / 1 zero** | — |

Eight of twelve cohorts have draw-level intervals spanning zero. Only 2017 is
unambiguous, with 100% of draws positive.

## 7. Does the matched effect track future exposure?

**No.** Spearman of matched relative ΔAP against the percentage of Arm-B
training rows dated after the test cohort: **+0.175** (+0.182 excluding 2024).

The cohort with the most future exposure (2013, 90.5%) is negative (−3.6%); the
largest positive (2017, +35.4%) sits at 55%; the strongest negatives (2021
−19.9%, 2016 −17.3%) sit at 24% and 63%. No gradient survives against test
positives (+0.112), baseline AP (−0.217), or cohort year (−0.175).

## 8. Final Channel 3 interpretation

**Channel 3 is an evaluation-protocol sensitivity result, not evidence of a
stable temporal-leakage inflation effect.**

Mechanism wording, stated with the care the evidence supports:

- **Same-CIK overlap is not supported as the dominant mechanism**, and the
  pre-declared grouped-CIK experiment provides **strong evidence against it**:
  driving same-CIK training overlap from 79.6% to 0% left the effect marginally
  larger (event-weighted +4.17% grouped against +2.59% ungrouped; sign preserved
  in 11 of 12 cohorts), and the rank correlation with same-CIK exposure is
  +0.091.
- **Future-population exposure is not supported as the dominant mechanism**: once
  training volume and positive count are matched, the effect does not scale with
  future exposure (+0.175) and the typical-cohort effect all but vanishes
  (median +11.87% → +0.04%).
- **Neither mechanism is claimed to be universally or causally excluded.** These
  are two designs, one panel, 341 positives, and twelve cohorts. Each finding
  bounds what these data support about dominance, not about existence. A
  mechanism can be real and still not dominate here, and a larger or differently
  constructed panel could resolve what this one cannot.
- **The residual differences are best described as cohort-specific
  training-composition sensitivity**: *which* observations train the model
  matters more than *when* they come from, and the direction of that sensitivity
  varies by cohort rather than pointing one way.

## 9. Artifacts

`outputs/gate2/gate2c_matched_volume.csv`, `gate2c_matched_volume.json`,
`gate2c_comparison.json`. Generated, untracked by design.
