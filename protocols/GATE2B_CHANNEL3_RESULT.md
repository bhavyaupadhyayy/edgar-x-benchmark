# Gate 2B Channel 3 Result — temporal evaluation / random splitting

**Date:** 2026-09-20
**Status:** FROZEN at commit `52d0700`. Results are not to be modified.
**Scope:** 12 rolling-testable cohorts, 2013–2024, strict validation-CIK excluded.
**Code:** `gate2b_temporal.py --all-cohorts`, `gate2b_temporal_summary.py`

---

## Formal conclusion

1. **8 of 12 cohorts have positive ΔAP.** Negative cohorts: 2016, 2020, 2021, 2024.
2. **The effect is heterogeneous**, ranging from −39.7% (2024) to +79.3% (2014)
   in relative terms.
3. **Event-weighted relative ΔAP is +2.6%** (absolute +0.00090).
4. **Its paired uncertainty includes zero**: paired CIK-cluster bootstrap 95% CI
   [−0.00359, +0.00844], P(ΔAP > 0) = 0.755.
5. **Individual aggregate estimators disagree materially** — pooled
   observation-level +16.2%, cohort median +11.9%, cohort mean +12.1%,
   event-weighted +2.6%. A factor-of-six spread driven purely by weighting.
6. **2024 is highly influential.** Leave-one-out on the event-weighted relative
   aggregate: dropping 2024 moves it from +2.6% to +9.8%, a +7.2pp shift, more
   than twice any other cohort's influence. Dropping 2014 or 2019 instead flips
   the aggregate negative.
7. **CIK grouping does not remove the difference.** The pre-declared grouped
   diagnostic drives same-CIK training overlap from 79.6% to 0% by construction,
   and the effect is marginally *larger*: event-weighted +4.17% grouped against
   +2.59% ungrouped, cohort median +12.13% against +11.87%, sign preserved in
   11 of 12 cohorts.
8. **Therefore same-firm train/test leakage is not the dominant mechanism.** The
   rank correlation between relative ΔAP and the share of test rows with a later
   same-CIK training row is +0.091 — effectively nil — despite that share
   ranging 71–91% across the first eleven cohorts.
9. **Training-volume asymmetry remains a major unresolved confound.** Arm A's
   training set grows from 24 positives (2013) to 309 (2024) while Arm B always
   trains on ≈273. Relative ΔAP correlates −0.476 with Arm-A training positives,
   −0.573 with baseline AP, and −0.476 with cohort year. The negative cohorts are
   concentrated where Arm A is best supplied.

## What this result is not

It is **not** evidence of a stable AP-inflation effect from non-temporal
splitting, and must not be reinterpreted as one. The channel is an
evaluation-protocol **sensitivity** result: the measured difference depends on
which aggregation rule is chosen, is dominated by one cohort, and is entangled
with a training-volume asymmetry that this design cannot separate.

## Cohort table

| year | test N | pos | AP strict | AP random | ΔAP | rel ΔAP | ΔAUC | bootstrap 95% CI | P(Δ>0) | score corr | later same-CIK | grouped rel ΔAP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2013 | 4,980 | 13 | 0.0095 | 0.0106 | +0.0011 | +11.9% | −0.0535 | [−0.0045, +0.0111] | 0.611 | 0.9099 | 88.2% | +22.4% |
| 2014 | 4,989 | 27 | 0.0160 | 0.0287 | +0.0127 | +79.3% | −0.0067 | [+0.0008, +0.0582] | 0.995 | 0.8820 | 86.5% | +47.0% |
| 2015 | 4,922 | 25 | 0.0140 | 0.0156 | +0.0016 | +11.8% | +0.0049 | [−0.0003, +0.0056] | 0.948 | 0.9147 | 86.1% | +10.7% |
| 2016 | 4,488 | 37 | 0.0540 | 0.0477 | −0.0064 | −11.8% | −0.0025 | [−0.0344, +0.0050] | 0.138 | 0.9257 | 87.0% | −19.3% |
| 2017 | 4,439 | 21 | 0.0103 | 0.0149 | +0.0047 | +45.2% | +0.0338 | [+0.0008, +0.0156] | 0.998 | 0.9354 | 88.6% | +43.1% |
| 2018 | 4,297 | 21 | 0.0248 | 0.0308 | +0.0060 | +24.4% | +0.0004 | [−0.0044, +0.0368] | 0.875 | 0.9468 | 88.7% | +40.1% |
| 2019 | 4,185 | 33 | 0.0757 | 0.0867 | +0.0109 | +14.4% | +0.0056 | [−0.0066, +0.0473] | 0.841 | 0.9573 | 89.6% | +24.8% |
| 2020 | 4,069 | 37 | 0.0329 | 0.0321 | −0.0008 | −2.3% | −0.0081 | [−0.0035, +0.0015] | 0.223 | 0.9730 | 91.3% | −5.5% |
| 2021 | 4,205 | 4 | 0.0351 | 0.0303 | −0.0048 | −13.8% | −0.0105 | [−0.0408, +0.0185] | 0.123 | 0.9720 | 91.0% | +2.5% |
| 2022 | 4,525 | 19 | 0.0128 | 0.0147 | +0.0019 | +15.0% | +0.0317 | [−0.0025, +0.0079] | 0.820 | 0.9738 | 86.3% | +7.0% |
| 2023 | 4,415 | 48 | 0.0342 | 0.0380 | +0.0039 | +11.3% | +0.0067 | [−0.0024, +0.0202] | 0.749 | 0.9888 | 71.0% | +13.6% |
| 2024 | 4,199 | 32 | 0.0501 | 0.0302 | −0.0199 | −39.7% | +0.0068 | [−0.0469, +0.0021] | 0.422 | 0.9962 | 0.5% | −32.5% |

The pilot's three cohorts reproduce exactly (2015 +11.81%, 2017 +45.17%,
2023 +11.28%), confirming the frozen setup ran unchanged. The pilot's +14.7%
pooled estimate **did not replicate in magnitude** at 12 cohorts, only in
direction.

## Artifacts

`outputs/gate2/temporal_pilot_results_full.csv`,
`temporal_predictions_{2013..2024}_full.csv`,
`temporal_bootstrap_{year}_full.npz`, `temporal_bootstrap_pooled_full.npz`,
`temporal_full_summary.json`. All generated, untracked by design.
