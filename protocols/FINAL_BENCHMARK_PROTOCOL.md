# Final Benchmark Protocol — EDGAR-X

**Date:** 2026-09-20
**Status:** pre-registration draft. **No benchmark model has been trained.** The
validation-CIK decision (§7) is deliberately left open.
**Predecessor:** `CONTAMINATION_FINDINGS_FREEZE.md` (contamination analysis closed at `63efd1b`)

---

## 1. Benchmark question

> How well can corporate bankruptcy within 365 days be predicted under a strictly
> point-in-time SEC information set, and what do ratios, filing text, and their
> combination contribute?

This is a **capability** question, not a contamination question. Nothing here is
optimised for, or reported against, any contamination effect. The contaminated
arms are closed.

## 2. Primary evaluation

- **Rolling temporal cohorts**, test years **2013–2024**, training only on
  observations available before the test cohort. Identical to the frozen Arm A of
  Channel 3.
- **Outcome definition unchanged**: initial US Chapter 7 or Chapter 11 petition by
  the same registrant within 365 days of the 10-K acceptance timestamp, per
  `LABEL_POLICY.md`. No label, chapter or horizon change.
- **Identity unchanged**: CIK as legal-registrant identity, no parent–child
  resolution.
- **Historical SIC unchanged**: `sic_as_filed` from DERA `sub.txt`, FIRE
  (6000–6799) excluded, unknown SIC excluded as its own state.
- **Headline metric: AP / PR-AUC.** Prevalence is ~0.6%, so AP is the honest
  summary and ROC-AUC is not.
- **Lift and fixed-review-budget metrics** as co-primary practical measures (§8).
- **Calibration** reported, not just discrimination.
- **ROC-AUC secondary.**

## 3. Feature arms — three, pre-specified

### A. Ratios-only
The existing strict-PIT financial-ratio pipeline, unchanged: the 15 ratios in
`gate2_panel.RATIO_NAMES`, built from as-filed DERA facts with the point-in-time
rule that a fact for period P may come only from a submission accepted at or
before the observation's own acceptance timestamp.

### B. Text-only
Point-in-time text from the eligible 10-K itself: **Item 1A Risk Factors** and
**Item 7 MD&A**, extracted by `gate3_item_extraction.py`.

**TF-IDF + regularised logistic regression.** A simple reproducible sparse
baseline, deliberately not a new neural architecture, not a transformer, not an
LLM. Word unigrams and bigrams, lowercased, English stop words removed, sublinear
term frequency, minimum document frequency 5, vocabulary capped (§8). The
vectoriser is **fit on the training fold only** in every cohort; fitting it on the
full corpus would leak future vocabulary and document frequencies, which is
exactly the class of error this project exists to measure.

### C. Ratios + text
One pre-specified combination, fixed before results: **horizontal concatenation**
of the standardised ratio block and the TF-IDF block into a single sparse design
matrix, with one logistic regression fitted over both. No stacking, no ensembling,
no learned gating, no per-arm weight search. If a second combination is ever
wanted it is a new pre-registration, not an edit here.

**Excluded from all arms:** LLM features, transformer fine-tuning, agents, macro
data, any new neural method, and any feature that reads information dated after
the observation's acceptance timestamp.

## 4. Text corpus status — acquisition is required and has not happened

**No 10-K document has ever been downloaded.** The cached corpus is `8k_text/`,
3,617 Item 1.03 8-K primary documents. The text arms cannot be built from local
data today.

The bulk submissions archive names a primary document for
**59,499 of 59,500 eligible observations (100.00%)**, including **every positive
in every cohort**, so the corpus is fully acquirable. Acquisition would be a
separate, explicitly approved step: 59,499 documents at the benchmark client's
8 requests/second is **≈2.1 hours** of SEC traffic plus retries, and must not run
concurrently with production EDGAR ingestion.

Inventory: `outputs/gate3/tenk_document_inventory.csv`.

## 5. Missing-text policy — fixed before any model runs

Missing text is a **legitimate state**, not an extraction failure to be hidden.
Smaller reporting companies are permitted to omit Item 1A entirely, and some
filings incorporate a section by reference.

1. **No observation is dropped for missing text.** The eligible observation set is
   identical across all three arms, so arms remain comparable and the ratios-only
   arm is never evaluated on a quietly easier population.
2. In arms B and C, an observation with a missing section contributes a **zero
   vector** for that section's TF-IDF block, plus an explicit **binary
   missingness indicator** per section (`item_1a_missing`, `item_7_missing`).
   Missingness is informative — it correlates with filer size — so it is modelled,
   not imputed away.
3. Every extraction outcome is recorded per observation and reported by cohort:
   `ok`, `no_heading`, `no_terminator`, `too_short`, `empty_document`,
   `document_unavailable`.
4. **Amendments are not merged.** The frozen observation unit is an exact
   `10-K`; a `10-K/A` is not an observation and its text never enters an
   observation's features. Pinned by test in `gate3_extraction_test.py`.
5. If any cohort's `ok` rate for a section falls below **70%**, the text arms are
   reported for that cohort with the coverage figure stated inline, and a
   coverage-restricted sensitivity analysis accompanies the primary result.

## 6. Extraction correctness — tested before the corpus exists

`gate3_extraction_test.py`, **24 checks, all passing**, against synthetic
fixtures isolating one boundary problem each:

- table-of-contents headings, with dot leaders and page numbers, must not be
  mistaken for substantive sections;
- Item 7 must terminate at Item 7A and never absorb market-risk text;
- Item 7 must terminate at Item 8 when Item 7A is absent, and never absorb the
  financial statements;
- Item 1A must terminate at Item 1B, or Item 2 when 1B is absent;
- Item 1A legitimately absent in older/smaller-company filings reports
  `no_heading` rather than inventing text, and does not block Item 7;
- duplicate substantive headings resolve to the real section;
- incorporation by reference reports `too_short`, never `ok`;
- malformed HTML degrades without raising and still yields bounded sections;
- heading spelling variants (`ITEM 1A.`, `Item 1A -`, `Item 1A:`, non-breaking
  space, en dash) are all recognised;
- `Item 7A` alone does not satisfy an `Item 7` start;
- the amendment policy holds.

The strategy is longest-candidate-section rather than first-match: every
candidate start is paired with its first following terminator and the longest
result above `MIN_SECTION_CHARS = 1000` wins, so a TOC entry is outscored
automatically rather than filtered by a heuristic that must recognise a TOC.

## 7. Validation-CIK handling — OPEN DECISION, not taken here

The 188 frozen validation CIKs audited **label quality**; they were never a
predictive test set. Two defensible choices follow, and this protocol does not
choose between them.

### Exact counts

| | Option A (exclude 188 validation CIKs) | Option B (complete frozen Gate 1 label set) | difference |
|---|---|---|---|
| observations, 2012–2024 | **58,789** | **59,500** | +711 |
| positives, 2012–2024 | **341** | **437** | **+96 (+28.2%)** |
| distinct CIKs | 9,466 | 9,586 | +120 |
| prevalence | 0.00580 | 0.00734 | ×1.266 |
| rolling-testable observations, 2013–2024 | **53,713** | **54,351** | +638 |
| rolling-testable positives, 2013–2024 | **317** | **408** | **+91 (+28.7%)** |
| cohorts with <10 positives | 2021 only | 2021 only | — |

Per cohort, positives A → B: 2012 24→29, 2013 13→16, 2014 27→32, 2015 25→36,
2016 37→44, 2017 21→27, 2018 21→25, 2019 33→45, 2020 37→45, 2021 4→5,
2022 19→28, 2023 48→61, 2024 32→44.

### Option A — primary benchmark excludes all frozen validation CIKs

Preserves exactly the separation used throughout Gate 2, so every benchmark
number is comparable to the contamination results without re-derivation.

*Implication:* discards 28.2% of the positive class in a study whose binding
constraint is already positive count. Gate 2A measured MDE 24–33% relative at
341 positives; Option A keeps the benchmark at that precision floor. It also
means the labels the study spent a full validation exercise auditing are absent
from the headline benchmark.

### Option B — primary benchmark uses the complete frozen Gate 1 label set

Justified because the validation sample audited label quality rather than
serving as a predictive holdout; the adjudication produced **no feature and no
model**, so reusing those registrants leaks nothing into the predictors. A
strict-exclusion (Option A) **sensitivity analysis** would accompany every
headline number.

*Implication:* +91 rolling-testable positives, prevalence up 27%, materially
better precision on every estimate. The cost is that two of the 95 audited
mapped positives are known label errors (the CCAA and same-name-subsidiary cases
in `FINAL_VALIDATION_REPORT.md`), so a small, quantified label-error rate enters
the benchmark. It also requires stating clearly in the paper why reuse is
legitimate, since a reader may assume "validation set" means "holdout".

**My assessment, for your decision:** Option B with an Option A sensitivity
analysis is the stronger design, because the validation exercise genuinely
produced no predictor and 28% more positives materially changes what this panel
can resolve. Option A is the more conservative presentation and the easier one to
defend without explanation. **Awaiting your decision; neither is implemented.**

## 8. Model selection protocol — frozen before any model runs

| item | specification |
|---|---|
| **Preprocessing, ratios** | the 15 frozen ratios; winsorised at the frozen `CLIPS` bounds; missing values imputed with the **training-fold** median; standardised with **training-fold** mean and standard deviation |
| **Preprocessing, text** | `TfidfVectorizer`, lowercase, English stop words, word 1–2 grams, `sublinear_tf=True`, `min_df=5`, `max_features=200_000`, **fitted on the training fold only** |
| **Feature dimensionality** | arm A: 15. arm B: ≤200,000 TF-IDF + 2 missingness indicators. arm C: arm A ⊕ arm B, concatenated sparse |
| **Regularization** | L2 logistic regression. Arm A keeps the frozen `C=1.0` for comparability with Gate 2. Arms B and C select `C` from a grid |
| **Hyperparameter grid** | `C ∈ {0.01, 0.1, 1.0, 10.0}` for arms B and C only. Nothing else is searched — no solver, penalty, n-gram, `min_df` or `max_features` search |
| **Rolling validation for selection** | for test cohort Y, the grid is scored by **expanding-window inner validation strictly inside the training data**: hold out the latest training cohort (Y−1), train on < Y−1, select the `C` maximising inner AP, then refit on all of < Y. **No test cohort, and no cohort ≥ Y, is ever consulted.** The same procedure runs identically for every cohort |
| **Class weighting** | `class_weight="balanced"`, identical in all arms |
| **Calibration** | isotonic regression fitted on the **inner** validation fold only; calibrated and uncalibrated metrics both reported; Brier score and a 10-bin reliability curve per cohort |
| **Missingness** | §5. Never a reason to drop an observation |
| **Random seeds** | vectoriser and solver are deterministic; any stochastic step uses seed **20260920**. Bootstrap inference reuses the frozen CIK-cluster procedure, 2,000 replicates, seed **20260916** |
| **Fixed review budgets** | precision@k and recall@k at **k ∈ {25, 50, 100, 250}** per cohort, plus **top-1%** of the cohort (≈42–50 filings). Lift@k = precision@k ÷ cohort prevalence |
| **Aggregation** | reported as a set, per the Channel 3 lesson: cohort median, cohort mean, event-weighted, and pooled — never one number alone |

Hyperparameters may not use future test cohorts. The model-selection procedure is
identical across cohorts and across arms.

## 9. Stop point

This protocol is pre-registration only. **No ratios, text or multimodal benchmark
model has been trained, and none will be until §7 is decided and this design is
approved.**

---

## Amendment 1 — decisions frozen before any benchmark model is trained (2026-09-20)

### 1. Primary benchmark population: Option B

**Option B is the primary benchmark**: the full frozen Gate 1 panel —
**59,500 observations, 437 positives**; rolling-testable 2013–2024
**54,351 observations / 408 positives**.

**Option A is a mandatory sensitivity analysis**: all 188 frozen
validation-sample CIKs excluded — rolling-testable **53,713 observations /
317 positives**. Every headline result is reported with its Option A counterpart.

**Rationale.** The 188-case exercise was a label-quality audit, not a predictive
model holdout. No AI adjudication label, classifier-disagreement signal, or
validation outcome is used as a feature, as a model target beyond the
pre-existing frozen Gate 1 labels, as a hyperparameter, or as test-time
information. **No Gate 1 label is modified on the basis of the AI adjudication.**
The full frozen Gate 1 label set therefore remains the primary benchmark, and
Option A tests whether any benchmark conclusion depends on validation-exposed
registrants.

### 2. Acquisition wording corrected

The earlier claim that 100% of observations were proven "acquirable" was wrong and
is withdrawn. What the offline inventory established is narrower:

- **named primary document: 59,499 / 59,500 observations**;
- **all 437 positives have a named primary document**;
- **one 2021 negative lacks a named primary document.**

**Actual document availability is not established until retrieval succeeds.**
Post-acquisition reporting separates: requested, HTTP success, permanently
unavailable, retryable failure, malformed/empty, byte count, and checksum.

### 3. Acquisition method

Approved and executed by `gate3_acquire_tenk.py`: the exact primary document of
each frozen 10-K accession, identifying SEC User-Agent, resumable via the
manifest, deterministic accession → primary-document mapping from the bulk
archive, atomic writes, bounded retries with backoff (3 attempts, 2 s then 6 s),
**no 10-K/A substitution and no amendment used in place of a missing original**,
raw bytes preserved (stored gzip-compressed; the recorded SHA-256 is of the
uncompressed payload), and a manifest carrying accession, CIK, acceptance
timestamp, form, primary-document name, local path, status, bytes and SHA-256.
No SEC payload is committed to git.

**One operational deviation, disclosed.** Measured single-threaded throughput was
**1.13 documents/second** against a 0.125 s rate floor — roughly 85% of wall time
was round-trip latency — projecting **14.6 hours**. The script therefore fetches
with `--workers 8` behind **one shared lock-guarded limiter capped at
`SEC_MAX_REQUESTS_PER_SECOND` = 8 rps**, which overlaps latency without raising
the request rate. Each worker's own `SecClient` throttle is made inert so the
shared limiter is the single governor rather than having two limiters neither of
which observes the true global rate. The cap was verified empirically: 80 grants
across 12 threads measured **8.09 rps**. Observed throughput is ~7.3 documents/s,
projecting ~2.2 hours. No production EDGAR ingestion ran concurrently.

### 4. Regularisation selection — identical for all three arms

The earlier asymmetry (arm A fixed at `C=1.0` while arms B and C tuned) is
removed. **All three arms use the same rule** over the same frozen grid:

**`C ∈ {0.01, 0.1, 1.0, 10.0}`**

For outer test cohort Y, the inner validation window is the **most recent
contiguous prior cohort(s) that together contain at least 25 positives**.
Candidate models train only on cohorts **preceding** that window. `C` is chosen
by **mean AP across the inner validation cohort(s)**, then the model is refit on
all observations strictly before Y. If there is insufficient earlier data to form
both an inner-training and an inner-validation period, the pre-registered
fallback **`C = 1.0`** applies. No test-year information enters selection. The
rule is applied identically to arms A, B and C.

Resolved windows under the primary population (Option B):

| test Y | inner validation | val pos | inner training | train pos | selection |
|---|---|---|---|---|---|
| 2013 | 2012 | 29 | none | 0 | **fallback C=1.0** |
| 2014 | 2012–2013 | 45 | none | 0 | **fallback C=1.0** |
| 2015 | 2014 | 32 | 2012–2013 | 45 | select C |
| 2016 | 2015 | 36 | 2012–2014 | 77 | select C |
| 2017 | 2016 | 44 | 2012–2015 | 113 | select C |
| 2018 | 2017 | 27 | 2012–2016 | 157 | select C |
| 2019 | 2018 | 25 | 2012–2017 | 184 | select C |
| 2020 | 2019 | 45 | 2012–2018 | 209 | select C |
| 2021 | 2020 | 45 | 2012–2019 | 254 | select C |
| 2022 | 2020–2021 | 50 | 2012–2019 | 254 | select C |
| 2023 | 2022 | 28 | 2012–2021 | 304 | select C |
| 2024 | 2023 | 61 | 2012–2022 | 332 | select C |

Under Option A the windows widen where positives are scarcer: 2018 uses
2016–2017, 2019 uses 2017–2018, 2022 uses 2020–2021, and 2023 uses 2020–2022;
2013 and 2014 again fall back to `C = 1.0`.

### 5. Calibration — isotonic removed from the primary protocol

**Isotonic calibration is removed.** With cohort positive counts this small, an
isotonic mapping fitted on one temporal validation window is unstable and can
manufacture apparent calibration structure from a handful of failures.

Primary benchmark outputs use the **raw logistic-regression probabilities** and
report: **Brier score, calibration intercept, calibration slope**, and a
**10-bin reliability summary where sample size permits** (bins with fewer than 5
observations are pooled or reported as unavailable rather than plotted).

**Models are not optimised on calibration performance.** Any post-hoc calibration
experiment must be separately declared; it is not part of this protocol.

### 6. Missing text — unchanged

Observations are **never dropped** because Item 1A or Item 7 is missing. A missing
section contributes a **zero sparse block** plus an explicit binary indicator
(`item_1a_missing`, `item_7_missing`). Amendments remain **separate
non-observations**: 10-K/A text is never merged into the original 10-K, pinned by
test in `gate3_extraction_test.py`.

### 7. Text representation — frozen decision

**Separate section-specific vocabularies.** Item 1A and Item 7 are vectorised by
**two independent `TfidfVectorizer` instances**, each fitted on the training fold
only, and their outputs are horizontally concatenated.

Rationale, recorded before any performance number exists: the same term carries a
different meaning in the two sections — a decline discussed in Risk Factors is
hypothetical, the same word in MD&A is realised — and a shared vocabulary
collapses that distinction. Separate blocks also keep the two missingness
indicators interpretable, since the sections go missing for different reasons.

**Dimensionality: `max_features = 100_000` per section, total text dimensionality
capped at 200,000**, plus the 2 missingness indicators. Both vectorisers use
lowercase, English stop words, word 1–2 grams, `sublinear_tf=True`, `min_df=5`.

No transformers, embeddings, LLM features, neural models, or additional document
sections.

### 8. Arm C combination — unchanged

One pre-specified horizontal concatenation: standardised ratio block ⊕ Item 1A
TF-IDF block ⊕ Item 7 TF-IDF block ⊕ 2 missingness indicators, under a single
logistic regression selected by the rule in §4 above. No stacking, ensembling or
learned gating.
