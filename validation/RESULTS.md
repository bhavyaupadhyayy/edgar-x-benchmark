# EDGAR-X Phase 2A — Human Validation Results

**Frozen 2026-09-23.** Executes only `HUMAN_VALIDATION_ANALYSIS_PLAN.md`, fixed
before any reviewer result was opened. Read `PROVENANCE.md` first: it records
what the procedure actually was.

All 188 frozen `case_id`s are present and identical to the committed packet. No
case was dropped, re-drawn, re-weighted or substituted. No benchmark model was
run and no Phase 1 label was changed.

## Four distinct objects, kept separate throughout

| object | what it is |
|---|---|
| **Classifier** | the automated EDGAR-X labeller; its disposition and observation-map membership are in the sealed key |
| **AI adjudicator** | the blinded AI that adjudicated this same holdout in Phase 1, **not** a reference standard here |
| **Reviewer A / B** | the two independent human first-pass reviewers |
| **Reviewer C** | the independent human adjudicator, who selected Reviewer A on every disputed field |
| **Final human consensus** | the Phase 2A reference standard; **equals Reviewer A exactly**, 188/188 on all four fields |

## Primary result

**Classifier mapped-positive confirmation rate against final human consensus.**

| | |
|---|---|
| Numerator | **92** |
| Denominator | **95** |
| Point estimate | **0.9684** |
| Wilson 95% CI | **[0.9112, 0.9892]** |

The denominator is the 95 mapped positive labels inside 2012–2024 in the frozen
holdout, fixed by the frozen sample and **not reduced** by deviations.

**"Cannot determine" treatment, exactly as frozen:** counted as *not confirmed*.
**Zero** of the 95 mapped positives received a "cannot determine" consensus, so
this rule did not affect the estimate. It is reported because the plan required
it to be fixed in advance, not because it bound.

The three not-confirmed cases are `V-db10d62faf`, `V-19b9fe683c`, `V-3aa349480a`.
The consensus records all three as **subsidiary/affiliate only**: the filing
debtor is an affiliate, not the exact registrant CIK.

**Comparison with Phase 1.** The AI adjudicator gave 93/95 = 0.9789,
[0.9265, 0.9942]. The independent human reference gives 92/95 = 0.9684,
[0.9112, 0.9892]. The intervals overlap heavily; the human estimate is very
slightly lower, consistent with the direction of the correlated-error concern but
**not** a statistically distinguishable difference on 95 cases.

## Secondary results

### Reviewer A against Reviewer B, first pass, before adjudication

| field | agree | n | rate |
|---|---|---|---|
| Disposition | 175 | 188 | 93.1% |
| Identity assessment | 164 | 188 | 87.2% |
| Initial chapter, both-positive cases | 136 | 137 | 99.3% |
| Petition date, both-positive cases | 137 | 137 | 100.0% |

No case was excluded for protocol deviation, so no denominator is reduced.

### Cohen's kappa, binary positive against non-positive

**κ = 0.872** on n = 188. Observed agreement 0.9521, expected 0.6270. Neither
marginal is degenerate, so kappa is **defined** and reported rather than
suppressed.

| | B positive | B non-positive |
|---|---|---|
| **A positive** | 137 | 1 |
| **A non-positive** | 8 | 42 |

### Classifier against final human consensus

**Chapter**, among human-confirmed positives whose classifier disposition names a
chapter: **91 / 92 = 98.9%**.

**Petition date**, exact match among human-confirmed positives with a date
resolvable under the consensus: **137 / 137 = 100.0%**. One case was excluded as
unresolvable under the consensus and is reported rather than dropped silently.

**Disposition across all 188 cases:** 139 / 188 = 73.9%
(classifier-positive and human-positive 92; classifier-positive human-negative 3;
classifier-negative human-positive 46; both negative 47).

> **This is not an accuracy figure and must not be read as one.** The holdout is
> stratified and deliberately oversamples ambiguous, subsidiary-only and
> receivership-only events. The 46 classifier-negative / human-positive cases are
> overwhelmingly events the classifier correctly declined to map onto a 10-K
> observation, for example because no eligible filing fell inside the horizon.
> No population accuracy, sensitivity, specificity, recall or prevalence is
> estimated from this sample, as the frozen plan forbids.

### AI adjudicator against final human consensus

Not a reference standard; reported under plan §6 as a separate object of study.

| scope | agree | n | rate |
|---|---|---|---|
| All 188 cases | 127 | 188 | 67.6% |
| The 95 mapped positives | 90 | 95 | 94.7% |

AI positive is defined as `ai_bankruptcy_event = yes` **and**
`ai_registrant_is_debtor = registrant` **and** `ai_initial_event = initial`,
since the AI form uses its own vocabulary rather than the reviewers' Yes/No. The
mapping is a stated analysis choice and part of why the all-188 figure is low.

**Interpretation.** On the mapped positives that drive the primary quantity, the
AI adjudicator and the human consensus agree 94.7% of the time. Across the full
stratified holdout they agree far less often. This is consistent with the Phase 1
concern that AI-adjudicator agreement was an optimistic reference, but the
all-188 gap is inflated by the vocabulary mapping and by the stratified design,
so it should not be quoted as a clean error rate for the AI.

## Adjudication

| quantity | value |
|---|---|
| Literal field-level A/B disagreements | **52** (27.7% of 188) |
| Of which vacuous, chapter-only, not applicable | **23** |
| Substantive disagreements routed to Reviewer C | **29** |
| Reviewer C rows supplied | 29 |
| Disputed cases missing from Reviewer C's form | 23, all vacuous |

The 23 vacuous cases all share one pattern: both reviewers answered "No" to
disposition, so the chapter question did not apply; Reviewer A left it blank and
Reviewer B wrote "Cannot determine". **The frozen plan defined disagreement
field-by-field with no not-applicable carve-out, so excluding these is a
declared post-hoc refinement, and both counts are reported.**

### Disagreement taxonomy

| code | all 52 literal | 29 substantive |
|---|---|---|
| `CHAPTER` | 39 | 16 |
| `IDENTITY` | 9 | 9 |
| `DETERMINABLE` | 4 | 4 |
| `DATE`, `INITIAL`, `FOREIGN`, `OTHER` | 0 | 0 |

Per-case detail is in `disagreements.csv`.

## Protocol deviations

**External-lookup contamination under Amendment 2: none.** Both reviewers'
rationale fields were scanned for disclosed use of a prohibited source. Zero
contaminated reviewer-case judgements, zero affected cases, **zero affected
mapped-positive cases.** No judgement was excluded, no case re-reviewed, no
denominator reduced.

Two procedural deviations are recorded in `PROVENANCE.md` and are **not**
external-lookup contamination:

1. Reviewer C adjudicated by a single blanket "select Reviewer A" decision rather
   than case-by-case, and supplied no per-case rationales.
2. The 23 vacuous chapter-only disagreements were not routed to Reviewer C, under
   a not-applicable rule absent from the frozen plan.

## What this does and does not establish

**Establishes.** The classifier's mapped-positive labels are confirmed by an
independent human reference standard at 92/95 = 96.8%, [0.9112, 0.9892]. The
reference standard was produced by humans who did not develop the classifier and
did not see its output, the AI adjudication, the answer key or the strata. Two
independent humans agreed on disposition in 93.1% of cases with κ = 0.872, so the
underlying judgement is reproducible between people. Chapter and petition date,
where the classifier commits to a specific value, agree at 98.9% and 100%.

**Does not establish.** This is not a population accuracy, recall or prevalence
estimate, and the stratified design does not support one. It is not a
two-reviewer consensus with independently reasoned adjudication: the reference
standard equals Reviewer A's judgement, ratified wholesale by Reviewer C. It does
not measure label recall, since events never disclosed under Item 1.03 remain
invisible. It does not license changing any Phase 1 benchmark label.

Phase 2A remains a **validation analysis**. Any label correction requires a
separate, explicitly approved, versioned dataset update.
