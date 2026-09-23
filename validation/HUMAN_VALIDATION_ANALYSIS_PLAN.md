# EDGAR-X — Human Validation Analysis Plan (Phase 2A)

**Status:** frozen 2026-09-23, before any reviewer result is opened.
**Companion to:** `HUMAN_VALIDATION_PROTOCOL.md`.

Every quantity reported from this study is defined here, in advance. Anything not
defined here is exploratory and must be labelled as such when reported.

## 1. Reference standard

The **final human consensus** of §6 of the protocol is the reference standard:
the A/B agreement where they agree, and reviewer C's adjudication on each
disputed field where they do not.

This is a **human consensus reference standard**, not ground truth. Court records
are not consulted. Where the consensus is "cannot determine", the case is
reported in a "cannot determine" category and is **not** silently dropped.

## 2. Primary quantity

**Classifier mapped-positive confirmation rate against the final human
consensus**, computed on the **same mapped-positive cases used by the existing
validation analysis** so the figure is directly comparable to the
AI-adjudicator figure of 93/95 = 0.9789, Wilson 95% CI [0.9265, 0.9942].

- **Denominator:** the mapped positive labels inside 2012–2024 in the frozen
  holdout, as identified in `sealed_key/final_validation_sample.csv`. The
  denominator is fixed by the frozen sample, not by what the reviewers return.
- **Numerator:** those cases where the final human consensus confirms that the
  exact registrant identified by the CIK is a debtor in an initial US Chapter 7
  or Chapter 11 proceeding.
- **Report:** numerator, denominator, point estimate, **Wilson 95% confidence
  interval**.
- The denominator is **not** reduced by protocol deviations. A mapped-positive
  case whose first-pass judgement was contaminated is re-reviewed under §4a and
  scored on the replacement; if it ends protocol-unresolved it counts as not
  confirmed. Whether any mapped-positive case was affected is reported.
- Cases whose consensus is "cannot determine" count as **not confirmed** in the
  primary estimate, and are additionally reported separately so the reader can
  see how many drove that choice. This is the conservative direction and is
  fixed now precisely so it cannot be chosen later.

## 3. Secondary quantities

Each is reported with its numerator and denominator.

1. **Binary disposition agreement**, classifier against final human consensus,
   over all 188 cases.
2. **Chapter agreement** among human-confirmed positives.
3. **Exact petition-date agreement** among human-confirmed positives **with a
   resolvable date under the consensus**. Cases where the consensus cannot
   resolve a date are excluded from this denominator and reported as a count.
4. **Disposition agreement across all 188 cases**, classifier against consensus.
5. **Reviewer A against Reviewer B agreement, before adjudication**, on each of:
   disposition, debtor identity, chapter, petition date.
6. **Number and percentage of cases requiring third-reviewer adjudication.**
7. **Disagreement taxonomy** (see §5).

## 4. Human-human reliability

Pre-specified, on the A/B first-pass labels only, before C adjudicates:

- **Raw agreement** on the binary positive / non-positive classification.
- **Cohen's kappa** for that binary classification.

Kappa is undefined or degenerate when either reviewer uses a single category
throughout, and unstable when the marginals are extreme. **If expected agreement
is 1, or either marginal is degenerate, kappa is reported as undefined with the
contingency table shown, and is not replaced by a substitute statistic chosen
after seeing the data.** Raw agreement and the 2x2 table are reported regardless.

Kappa is reported for the binary classification only. It is not computed for
chapter or petition date, where the category structure does not support it.

Both statistics are computed on first-pass judgements that are **not**
protocol-contaminated (§4a). Cases excluded by that rule are removed pairwise,
and the reduced denominator is reported next to the statistic.

## 4a. Protocol deviations: disclosed external lookups

Fixed by `human_validation/AMENDMENT_02_PROTOCOL_DEVIATIONS.md`, adopted
2026-09-23 before any reviewer received a packet. Summarised here because it
changes denominators.

A reviewer-case judgement is **protocol-contaminated** if the reviewer disclosed
using a prohibited external source for that case. Contamination attaches to that
one judgement, not to the reviewer and not to the case.

- The case **stays** in the 188-case sample. Nothing is dropped or re-drawn.
- The contaminated judgement is **excluded from first-pass A-against-B agreement
  and from Cohen's kappa for that case**, by pairwise deletion. The reduced
  denominator and the number excluded are reported with every affected statistic.
- The contaminated judgement **cannot establish final human consensus** and is
  never shown to the adjudicating reviewer.
- The case is **independently re-reviewed** by a fresh eligible reviewer who sees
  only the frozen packet and the same questionnaire, and who is shown neither the
  contaminated judgement, nor the other first-pass judgement, nor classifier
  output, nor the AI adjudication, nor any answer-key field or stratum.
- The normal consensus and adjudication rule then applies to the uncontaminated
  judgements only.
- After two failed replacement attempts for the same reviewer-case slot, the case
  is reported as **protocol-unresolved**, stays in the sample, and counts as **not
  confirmed** in the primary quantity, matching the treatment of "cannot
  determine" fixed in §2.
- The report states the number of contaminated judgements, the number of affected
  cases, the cause of each, **whether any primary mapped-positive case was
  affected**, and the reduced denominators.
- Contaminated judgements are retained and flagged in the committed reviewer
  files, never deleted, so the deviation and its replacement stay auditable.

Suspicion is not contamination: only a disclosure, or independently established
use, triggers this rule. No judgement is set aside for being inconvenient.

## 5. Disagreement taxonomy

Every A/B disagreement is classified into exactly one of:

| code | meaning |
|---|---|
| `IDENTITY` | disagreement over whether the exact registrant, rather than an affiliate, subsidiary or parent, is the debtor |
| `CHAPTER` | agreement that the registrant is a debtor, disagreement over Chapter 7 against Chapter 11 |
| `DATE` | agreement on disposition and chapter, disagreement over the petition date |
| `INITIAL` | disagreement over whether the proceeding is an initial filing or a conversion |
| `DETERMINABLE` | one reviewer answers "cannot determine", the other gives a substantive answer |
| `FOREIGN` | disagreement over whether a foreign proceeding qualifies |
| `OTHER` | anything else, described individually |

Counts per code are reported. Codes are assigned from the reviewers' own
rationales, before C adjudicates.

## 6. Comparison with the AI adjudication

The AI adjudication is **not** the reference standard. It is compared against the
human consensus as a separate, secondary object of study:

- AI-against-human-consensus agreement on disposition, over all 188 cases.
- The count of cases where AI and human consensus diverge, with the classifier's
  own label shown alongside, so a reader can see whether AI error was correlated
  with classifier error.

If AI-against-human agreement is materially lower than classifier-against-AI
agreement, that is direct evidence for the correlated-error concern stated in
Phase 1, and will be reported as such.

## 7. What will not be computed

Fixed now so it cannot be revisited after seeing results.

- **No population accuracy or recall estimate** will be produced from this
  stratified validation sample. The frozen sampling design supports a statement
  about label precision on discovered events; it does not support a recall or
  population-accuracy claim, and none will be made.
- **Agreement will not be called accuracy.** The reference standard is a human
  consensus, and it will be named as such wherever a figure is reported.
- **No inverse-probability-weighted population estimate** will be reported
  unless a separate amendment to this plan is frozen and dated before the
  weighting is applied.
- **No case will be excluded for low reviewer confidence.** The confidence field
  is descriptive only. It may be used to describe the distribution of confidence,
  and to report agreement stratified by confidence as an explicitly exploratory
  analysis, but never to discard a label.
- **No benchmark label will be corrected** as part of this analysis (§8 of the
  protocol).

## 8. Reporting

Results go into a new frozen document, `HUMAN_VALIDATION_REPORT.md`, with the
reviewer answer files and their hashes committed at the same time. The Phase 1
documents and working paper v1 are not edited. Any manuscript revision is a new
paper version.

If the study cannot be completed, for example because independent reviewers
cannot be recruited, that outcome is reported and the Phase 1 limitation stands
unchanged. A partial or abandoned study must not be reported as a validation.
