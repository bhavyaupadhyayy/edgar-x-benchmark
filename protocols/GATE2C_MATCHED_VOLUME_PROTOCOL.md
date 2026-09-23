# Gate 2C — matched-volume mechanism diagnostic

> **POST-HOC MECHANISM DIAGNOSTIC, MOTIVATED BY THE COMPLETED CHANNEL 3
> EXPERIMENT. IT IS NOT PRE-REGISTERED CONFIRMATION AND MUST NEVER BE PRESENTED
> AS SUCH.**

**Date:** 2026-09-20
**Motivation:** `GATE2B_CHANNEL3_RESULT.md` conclusion 9 — training-volume
asymmetry is an unresolved confound in the random-vs-rolling comparison.
**Status of Channel 3:** frozen at `52d0700` and not modified by anything here.

---

## Research question

> When training-set size and positive count are held fixed, does allowing
> future-period observations into training still change bankruptcy-prediction
> performance?

## Arms

For each rolling-testable cohort 2013–2024.

**Arm A — strict temporal.** The exact frozen strict-temporal training and test
sets from Channel 3: train on all observations with cohort year < Y, test on
cohort Y. Preprocessing, ratio definitions, model and validation-CIK exclusion
are unchanged. Equivalence is asserted mechanically: this diagnostic recomputes
Arm A and **aborts unless its AP reproduces the frozen Channel 3 value to
1e-9** for every cohort.

**Arm B — matched-volume future-inclusive.** The same test observations as
Arm A. Training data is drawn from **all eligible non-test observations**,
including future years where available, subject to exact matching:

- the same total number of training observations as Arm A;
- the same number of positive training observations as Arm A;
- therefore the same number of negatives as Arm A.

This removes the training-volume and positive-count advantage that Channel 3
could not separate from future information. **Which** future rows are selected is
never optimised: positives and negatives are drawn uniformly at random without
replacement from their respective non-test pools.

## Repeated sampling — frozen before results

- **100 matched draws** per cohort.
- Seed for cohort Y, draw d: `20260921 + 1000 * (Y - 2013) + d`. Fixed here,
  before any Arm B result was inspected.
- Every draw preserves the exact Arm-A training N and positive count.
- **No draw is discarded for any reason.** All 100 enter every statistic.

## Reporting, per cohort

Arm-A training N and positives; Arm-B training N and positives (identical by
construction); percentage of Arm-B training rows dated after the test cohort;
AP strict; mean and median AP across matched draws; signed ΔAP; relative ΔAP;
the distribution across draws; the 95% interval across the frozen draws; how
often ΔAP is positive across draws; ROC-AUC as a secondary metric.

## Structural negative control — 2024

**2024 is the negative control for future-period contamination.** No post-2024
cohort exists, so for Y = 2024 the non-test pool is *exactly* the Arm-A training
set: 54,590 observations and 309 positives either way. The matched-volume
procedure is therefore forced to reproduce Arm A identically, and ΔAP must be
**0.000 with zero variance across draws**.

If the procedure produces a substantial 2024 difference anyway, that difference
**cannot** be attributed to future-period information; it would reflect a
sampling or composition artifact in the procedure itself and must be reported as
such. 2024 is not hidden and not removed.

## Excluded by construction

No new models, no text, no LLM features, no macro variables, no new split
variants, no new leakage mechanisms, no label changes, no horizon changes.
Channel 1 and Channel 2 are not rerun.

## Interpretation rules

Significance is not the only decision rule.

- **If the effect largely disappears** — conclude that the original
  random-vs-rolling difference was primarily driven by training-volume and
  training-composition asymmetry rather than future-information leakage itself.
- **If a positive effect remains across most cohorts**, especially if it is
  larger in cohorts with meaningful future exposure and approximately absent in
  2024 — conclude that there is evidence for a genuine future-population
  temporal component beyond training volume.
- **If results remain highly heterogeneous** — report Channel 3 as an
  evaluation-protocol sensitivity result rather than a stable leakage effect.

**No further experiment will be invented to rescue this channel.**
