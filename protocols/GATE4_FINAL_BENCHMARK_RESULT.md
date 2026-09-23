# Gate 4 Final Benchmark Result — strict point-in-time bankruptcy prediction

**Date:** 2026-09-22
**Status:** FROZEN. No further model training, feature engineering, hyperparameter
search, sensitivity analysis, leakage experiment or extractor change.
**Protocol:** `FINAL_BENCHMARK_PROTOCOL.md` + Amendment 1, frozen at `aed29b4`
**Code:** `gate4_benchmark.py`, `gate4_summarize.py`, `gate4_build_text_cache.py`

---

## 1. Design as executed

Rolling temporal evaluation, test cohorts **2013–2024**, training only on prior
cohorts. Outcome, identity, horizon and SIC rules unchanged from Gate 1.

| arm | features |
|---|---|
| **A ratios** | 15 strict-PIT financial ratios |
| **B text** | Item 1A + Item 7, two separately fitted TF-IDF blocks (100,000 features each, fitted on the outer training period only) + 2 missingness indicators |
| **C combined** | ratios + both text blocks + indicators, one logistic regression; no stacking, no ensembling |

Populations: **B** primary (59,500 obs / 437 positives; rolling-testable 54,351 /
408), **A** sensitivity (188 validation CIKs removed), **DUP** sensitivity
(8 byte-identical cross-target observations removed). 36 units total.

## 2. Cohort results — Option B primary

| year | n | pos | AP A | AP B | AP C | AUC A | AUC B | AUC C | B−A | C−A | C−B |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2013 | 5,048 | 16 | 0.0147 | 0.0239 | 0.0441 | 0.8316 | 0.8706 | 0.8932 | +0.0092 | +0.0295 | +0.0203 |
| 2014 | 5,060 | 32 | 0.0145 | 0.0479 | 0.0312 | 0.6815 | 0.8125 | 0.7962 | +0.0333 | +0.0166 | −0.0167 |
| 2015 | 4,990 | 36 | 0.0170 | 0.0477 | 0.0535 | 0.7481 | 0.8100 | 0.8586 | +0.0307 | +0.0365 | +0.0058 |
| 2016 | 4,553 | 44 | 0.0601 | 0.1360 | 0.1533 | 0.7831 | 0.9024 | 0.8785 | +0.0759 | +0.0932 | +0.0173 |
| 2017 | 4,492 | 27 | 0.0146 | 0.0360 | 0.0794 | 0.6940 | 0.8605 | 0.8510 | +0.0214 | +0.0648 | +0.0435 |
| 2018 | 4,350 | 25 | 0.0312 | 0.1279 | 0.1485 | 0.8366 | 0.8995 | 0.9234 | +0.0967 | +0.1173 | +0.0206 |
| 2019 | 4,240 | 45 | 0.0901 | 0.1577 | 0.2384 | 0.7540 | 0.8739 | 0.8475 | +0.0676 | +0.1482 | +0.0806 |
| 2020 | 4,111 | 45 | 0.0332 | 0.3533 | 0.2412 | 0.7971 | 0.9390 | 0.9469 | +0.3201 | +0.2080 | **−0.1121** |
| 2021 | 4,251 | 5 | 0.0266 | 0.3847 | 0.4809 | 0.9009 | 0.9965 | 0.9951 | +0.3581 | +0.4543 | +0.0962 |
| 2022 | 4,575 | 28 | 0.0232 | 0.0386 | 0.0771 | 0.7338 | 0.7867 | 0.8287 | +0.0154 | +0.0539 | +0.0385 |
| 2023 | 4,456 | 61 | 0.0475 | 0.1673 | 0.2060 | 0.7191 | 0.8708 | 0.8750 | +0.1198 | +0.1585 | +0.0386 |
| 2024 | 4,225 | 44 | 0.0678 | 0.0705 | 0.0928 | 0.7221 | 0.8579 | 0.8817 | +0.0027 | +0.0250 | +0.0223 |

**2021 carries only 5 positives.** Its AP figures are individually near-meaningless
and inflate the cohort mean and median views; event weighting gives it 1.2%.

## 3. Selected C

2013 and 2014 took the pre-registered **`C = 1.0` fallback** in every population
and arm, as specified — no inner split exists for them. Selection is active from
2015 onward.

Text and combined models selected **`C = 10` in 8 of the final 10 cohorts**.
Stated precisely: **the temporal selection procedure frequently preferred the
weakest regularisation available in the frozen grid.** This is not a claim that
`C = 10` is globally optimal, and the grid was not expanded.

Arm A spans the full grid across cohorts (0.01 → 10.0). Full table:
`gate4_release/selected_c.csv`.

## 4. Aggregates — Option B

| arm | median AP | mean AP | event-weighted AP | pooled AP¹ | pooled AUC¹ |
|---|---|---|---|---|---|
| A ratios | 0.0289 | 0.0367 | **0.0425** | 0.0246 | 0.7523 |
| B text | 0.0992 | 0.1326 | **0.1301** | 0.0489 | 0.7719 |
| C combined | 0.1206 | 0.1539 | **0.1447** | 0.0769 | 0.7954 |

¹ **Pooled observation-level stacks 12 differently-scaled models onto one
ranking.** Reported for completeness; it is not a headline and must not be quoted
as the sole aggregate.

## 5. Paired comparisons — 2,000 CIK-cluster replicates, seed 20260916

| contrast | median | mean | event-wtd | rel. event-wtd | cohorts +/− |
|---|---|---|---|---|---|
| **B − A** | +0.0505 | +0.0959 | **+0.0876** | **+206.11%** | **12 / 0** |
| **C − A** | +0.0790 | +0.1172 | **+0.1022** | **+240.30%** | **12 / 0** |
| **C − B** | +0.0214 | +0.0212 | **+0.0145** | **+11.17%** | **10 / 2** |

### B − A per cohort

| year | ΔAP | rel | 95% CI | P(Δ>0) |
|---|---|---|---|---|
| 2013 | +0.0092 | +62.7% | [−0.0025, +0.0304] | 0.942 |
| 2014 | +0.0333 | +229.2% | [+0.0057, +0.0959] | 0.995 |
| 2015 | +0.0307 | +180.6% | [+0.0082, +0.0785] | 0.998 |
| 2016 | +0.0759 | +126.2% | [+0.0251, +0.1403] | 0.998 |
| 2017 | +0.0214 | +146.8% | [+0.0080, +0.0590] | 1.000 |
| 2018 | +0.0967 | +309.7% | [+0.0313, +0.2139] | 0.999 |
| 2019 | +0.0676 | +75.0% | [−0.0407, +0.1780] | 0.893 |
| 2020 | +0.3201 | +964.2% | [+0.1896, +0.4669] | 1.000 |
| 2021 | +0.3581 | +1348.8% | [+0.0450, +0.7623] | 1.000 |
| 2022 | +0.0154 | +66.5% | [−0.0191, +0.0997] | 0.780 |
| 2023 | +0.1198 | +252.1% | [+0.0421, +0.2225] | 1.000 |
| 2024 | +0.0027 | +4.1% | [−0.0798, +0.0677] | 0.580 |

**Eight of twelve** intervals exclude zero: 2014, 2015, 2016, 2017, 2018,
2020, 2021 and 2023. The four that include zero are 2013, 2019, 2022 and
2024. (See the erratum at the end of this document.)

### C − A per cohort

Positive in all 12; intervals exclude zero in 10. Weakest: 2024
(+0.0250, [−0.0525, +0.1050], P=0.816) and 2022 (+0.0539, [−0.0046, +0.1490],
P=0.953).

### C − B per cohort

| year | ΔAP | rel | 95% CI | P(Δ>0) |
|---|---|---|---|---|
| 2013 | +0.0203 | +84.9% | [−0.0004, +0.0878] | 0.972 |
| 2014 | −0.0167 | −34.9% | [−0.0655, +0.0045] | 0.061 |
| 2015 | +0.0058 | +12.1% | [−0.0168, +0.0299] | 0.687 |
| 2016 | +0.0173 | +12.7% | [−0.0128, +0.0708] | 0.845 |
| 2017 | +0.0435 | +120.8% | [+0.0040, +0.1435] | 0.988 |
| 2018 | +0.0206 | +16.1% | [−0.0097, +0.0737] | 0.925 |
| 2019 | +0.0806 | +51.1% | [−0.0084, +0.1795] | 0.960 |
| **2020** | **−0.1121** | **−31.7%** | **[−0.2037, −0.0195]** | **0.008** |
| 2021 | +0.0962 | +25.0% | [−0.0467, +0.3555] | 0.680 |
| 2022 | +0.0385 | +99.8% | [+0.0003, +0.0745] | 0.977 |
| 2023 | +0.0386 | +23.1% | [−0.0101, +0.0883] | 0.945 |
| 2024 | +0.0223 | +31.6% | [+0.0058, +0.0574] | 0.997 |

**C−B is positive in 10/12 cohorts. Four cohort intervals exclude zero:
three positively (2017, 2022, 2024) and 2020 negatively.**

## 6. Calibration diagnostics — raw frozen logistic outputs only

**No arm is described as calibrated, and none is.** `class_weight="balanced"`
changes the probability scale, most severely for Arm A, whose Brier scores
(0.197–0.238) reflect systematically inflated probabilities at ~0.7% prevalence
rather than poor ranking. **No post-hoc recalibration experiment was run.**

**AP, ROC-AUC and the review-budget metrics are ranking-oriented and are the main
predictive comparisons.** Brier score, calibration intercept and calibration
slope characterise the raw frozen logistic outputs only.

| year | Brier A | Brier B | Brier C | int A | slope A | int B | slope B | int C | slope C |
|---|---|---|---|---|---|---|---|---|---|
| 2013 | 0.21639 | 0.00579 | 0.00709 | −5.812 | 0.659 | −2.722 | 1.007 | −2.870 | 0.984 |
| 2014 | 0.19707 | 0.00755 | 0.00855 | −4.913 | 0.420 | −1.414 | 1.104 | −2.280 | 0.790 |
| 2015 | 0.21934 | 0.00889 | 0.00844 | −4.908 | 0.767 | −2.115 | 0.548 | −1.789 | 0.644 |
| 2016 | 0.23073 | 0.01340 | 0.00984 | −4.868 | 1.059 | −1.771 | 1.113 | −1.316 | 0.769 |
| 2017 | 0.22186 | 0.15962 | 0.05911 | −5.057 | 0.573 | −4.551 | 2.358 | −3.950 | 1.083 |
| 2018 | 0.22116 | 0.00578 | 0.00560 | −5.403 | 1.193 | −0.695 | 0.965 | −0.609 | 0.979 |
| 2019 | 0.21112 | 0.01017 | 0.04797 | −4.625 | 0.978 | −0.797 | 0.823 | −3.080 | 1.258 |
| 2020 | 0.22328 | 0.00986 | 0.06774 | −4.606 | 0.914 | −1.079 | 0.997 | −3.582 | 1.677 |
| 2021 | 0.21441 | 0.00242 | 0.00332 | −7.377 | 1.391 | −2.509 | 1.325 | −3.074 | 1.215 |
| 2022 | 0.20294 | 0.00615 | 0.00604 | −5.029 | 0.717 | −1.536 | 0.498 | −1.106 | 0.630 |
| 2023 | 0.23120 | 0.01372 | 0.01361 | −4.318 | 0.677 | −1.209 | 0.686 | −1.269 | 0.713 |
| 2024 | 0.23785 | 0.01291 | 0.01355 | −4.662 | 0.789 | −1.809 | 0.675 | −1.843 | 0.700 |

## 7. Review-budget metrics — event-weighted

**Operational ranking results, not deployment claims.**

| metric | A ratios | B text | C combined |
|---|---|---|---|
| precision@25 | 0.0672 | 0.1925 | **0.2294** |
| recall@25 | 0.0392 | 0.1176 | 0.1397 |
| lift@25 | 6.88× | 20.60× | **24.46×** |
| precision@50 | 0.0641 | 0.1601 | 0.1928 |
| recall@50 | 0.0735 | 0.2010 | 0.2377 |
| lift@50 | 6.47× | 17.67× | 20.98× |
| precision@100 | 0.0494 | 0.1314 | 0.1389 |
| recall@100 | 0.1225 | 0.3235 | **0.3456** |
| lift@100 | 5.41× | 14.33× | 15.27× |
| precision@250 | 0.0392 | 0.0829 | 0.0834 |
| recall@250 | 0.2549 | 0.5074 | 0.5147 |
| lift@250 | 4.56× | 9.03× | 9.17× |
| precision@top-1% | 0.0610 | 0.1725 | **0.1998** |
| recall@top-1% | 0.0613 | 0.1912 | 0.2181 |
| lift@top-1% | 6.10× | 19.06× | 21.76× |

## 8. Option A sensitivity — 188 validation CIKs excluded

| arm | median | mean | event-wtd |
|---|---|---|---|
| A | 0.0283 | 0.0318 | 0.0360 |
| B | 0.0661 | 0.1086 | 0.1079 |
| C | 0.1011 | 0.1428 | 0.1267 |

| contrast | event-wtd | relative | cohorts +/− |
|---|---|---|---|
| B − A | +0.0718 | **+199.37%** | **12 / 0** |
| C − A | +0.0906 | **+251.45%** | **12 / 0** |
| C − B | +0.0188 | +17.40% | 9 / 3 |

## 9. Duplicate-content sensitivity — 8 byte-identical observations excluded

| arm | median | mean | event-wtd |
|---|---|---|---|
| A | 0.0289 | 0.0367 | 0.0425 |
| B | 0.1009 | 0.1356 | 0.1355 |
| C | 0.1221 | 0.1525 | 0.1430 |

| contrast | event-wtd | relative | cohorts +/− |
|---|---|---|---|
| B − A | +0.0930 | **+218.93%** | **12 / 0** |
| C − A | +0.1005 | **+236.38%** | **12 / 0** |
| C − B | +0.0074 | +5.47% | 9 / 3 |

All 8 excluded observations are negatives, so the effect is minimal by
construction.

## 10. Leave-one-cohort-out influence — Option B, event-weighted

| dropped | AP A | AP B | AP C | B−A | C−B |
|---|---|---|---|---|---|
| none | 0.0425 | 0.1301 | 0.1447 | +0.0876 | +0.0145 |
| 2013 | 0.0436 | 0.1345 | 0.1488 | +0.0908 | +0.0143 |
| 2014 | 0.0449 | 0.1371 | 0.1543 | +0.0922 | +0.0172 |
| 2015 | 0.0450 | 0.1381 | 0.1535 | +0.0931 | +0.0154 |
| 2016 | 0.0404 | 0.1294 | 0.1436 | +0.0890 | +0.0142 |
| 2017 | 0.0445 | 0.1368 | 0.1493 | +0.0923 | +0.0125 |
| 2018 | 0.0432 | 0.1303 | 0.1444 | +0.0870 | +0.0141 |
| 2019 | 0.0366 | 0.1267 | 0.1330 | +0.0901 | +0.0063 |
| **2020** | 0.0437 | 0.1025 | 0.1327 | **+0.0588** | **+0.0302** |
| 2021 | 0.0427 | 0.1270 | 0.1405 | +0.0843 | +0.0135 |
| 2022 | 0.0439 | 0.1369 | 0.1496 | +0.0929 | +0.0128 |
| 2023 | 0.0416 | 0.1236 | 0.1339 | +0.0820 | +0.0103 |
| 2024 | 0.0395 | 0.1373 | 0.1509 | +0.0979 | +0.0136 |

**2020 is the single influential cohort.** Dropping it cuts B−A by 33%
(+0.0876 → +0.0588) and doubles C−B (+0.0145 → +0.0302). No other cohort moves
either contrast by more than ~12%. B−A remains large and positive under every
deletion.

---

## Frozen primary conclusions

### Finding 1 — point-in-time 10-K text adds substantial predictive signal beyond financial ratios

- B−A positive in **12/12** primary cohorts
- event-weighted AP **0.0425** ratios versus **0.1301** text
- event-weighted **ΔAP = +0.0876**, relative **+206%**
- preserved under Option A (**+199%, 12/0**) and duplicate-content (**+219%, 12/0**)

### Finding 2 — combining text and ratios clearly outperforms ratios alone

- C−A positive in **12/12** cohorts
- event-weighted AP **0.1447**
- relative improvement over ratios **+240%**

### Finding 3 — ratios add only modest and heterogeneous incremental signal beyond text

- C−B event-weighted **ΔAP = +0.0145**, **+11.2%** relative
- positive in **10/12** cohorts
- four cohort intervals exclude zero: **three positively** (2017, 2022, 2024)
  and **2020 negatively**
- **2020 is significantly negative** (−0.1121, [−0.2037, −0.0195], P=0.008)

**Do not claim that combined features uniformly outperform text.**

### Finding 4 — review-budget performance improves materially with text

- precision@25: A 0.067, B 0.193, C 0.229
- recall@100: A 0.123, B 0.324, C 0.346
- top-1% precision: A 0.061, B 0.173, C 0.200

**Operational ranking results, not deployment claims.**

---

## Reproducibility

Tracked, compact (72 KB): `gate4_release/cohort_metrics.csv`,
`aggregate_metrics.csv`, `selected_c.csv`, `leave_one_cohort_out.csv`,
`artifact_manifest.csv`.

Untracked and hashed in the manifest: 36 prediction files, the benchmark summary
JSON, and the Gate 2/3 panel, extraction-outcome, acquisition-manifest,
retrieval-accounting and QA artifacts (44 artifacts, 103.5 MB). No SEC document
payload and no text cache is committed.

Regeneration, in order, from the frozen corpus:

```
python3 gate4_build_text_cache.py --workers 8     # verifies 0 mismatches vs the frozen audit
python3 gate4_benchmark.py                        # resumable, 36 units, ~12 h
python3 gate4_summarize.py
```

---

## Erratum — 2026-09-22

**Prose transcription correction only. No interval, prediction, bootstrap
result, aggregate, sign count or headline result is modified.**

1. **B − A interval count.** This document originally stated "Nine of twelve
   intervals exclude zero" for the text-over-ratios contrast. The authoritative
   per-cohort intervals in `gate4_release/cohort_metrics.csv` imply **eight of
   twelve**: 2014, 2015, 2016, 2017, 2018, 2020, 2021 and 2023 exclude zero;
   2013, 2019, 2022 and 2024 include it. The interval values themselves were and
   remain correct in both artifacts; only the tally was wrong.

2. **C − B interval wording.** The original phrasing "only three intervals
   exclude zero, and 2020 is significantly negative" could be read as claiming
   three intervals exclude zero in total. Corrected throughout to: **C−B is
   positive in 10/12 cohorts; four cohort intervals exclude zero, three
   positively and 2020 negatively.**

Unaffected: the text-over-ratios contrast remains positive in **12 of 12**
cohorts with event-weighted ΔAP **+0.0876** (**+206%** relative), and every
other figure in this document stands as originally frozen.
