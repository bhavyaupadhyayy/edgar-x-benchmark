# Final Validation Protocol

> **Historical document, superseded in part.** This records the *first*
> validation pass, which used a blinded AI adjudicator. An independent human
> adjudication of the same frozen holdout was completed afterwards and is the
> evidence the working paper relies on; see `RESULTS.md`, `PROVENANCE.md` and
> `HUMAN_VALIDATION_PROTOCOL.md` in this directory. Statements below about
> human adjudication being outstanding were true when written and are no longer
> current. Nothing here has been edited.

Pre-registered before the holdout was drawn. Adopted 2026-09-16, on classifier
commit `f23e54f` (stage 5) with the corrected Gate 1 rerun of 2026-09-15.

This document is frozen. Anything decided after the sample is drawn belongs in a
separate document, not here.

## What is being validated

The corrected Gate 1 population of 3,010 assembled bankruptcy events, produced by
the repaired classifier (stages 1–5) under `LABEL_POLICY.md`. Gate 2 has not run.

## Eligibility: untouched at event AND CIK level

An event is **ineligible** for final validation if either:

1. the event or any of its accessions was development-exposed, or
2. **any other event of the same CIK** was development-exposed.

Exposure is enumerated in `DEV_EXPOSURE_REGISTRY.csv` (1,660 events, 2,021
accessions), covering: the 290-event LLM development audit; the 104 excluded
development examples; the 57-case second-AI review, its shortlist and the blind
review packet; stage 1–5 regression fixtures; stage-transition investigations;
every manually inspected demotion and recovery; seeded corpus samples;
co-registration investigations; duplicate and event-identity investigations;
date-parser investigations; and every filing named in a development log or report.

The eligible frame is `UNTOUCHED_VALIDATION_FRAME_CIK_CLEAN.csv`. The whole
sample drawn from it is untouched at both event and CIK level.

## Adjudication

- **Final labels are adjudicated by a human, not an LLM.** No LLM verdict may be
  recorded as a final label, and no earlier LLM annotation carries over.
- The human reviewer is **blinded** to: the automated disposition, the automated
  petition date, the mechanism tag, all development annotations, and the sampling
  stratum. Those live only in `final_validation_key.csv`
  (`final_human_review_key.csv`), which the reviewer does not open.
- The reviewer sees only: an opaque case id, registrant name, CIK, accession
  numbers, the substantive Item 1.03 text, the nearby filing text needed to settle
  debtor identity and the petition date, amendment text where relevant, and blank
  answer fields.
- Review order is randomised independently of stratum.

## What this holdout can and cannot estimate

- **Primary-window validation estimates the precision of the 2012–2024 mapped
  positive labels** — the rules-positive events that actually label a 10-K
  observation in the benchmark cohorts.
- **Because all 31 mapped ambiguous events inside 2012–2024 were
  development-exposed, this holdout cannot provide an untouched direct estimate of
  ambiguous-bucket recall inside the 2012–2024 window.** No such estimate may be
  computed from this sample, and the upper bound cannot be validated here.
- Validation of the ambiguous, subsidiary-only, receivership-only,
  prospective-only and foreign-proceeding-only strata drawn from the broader
  untouched population is a **secondary classifier-error audit, not an in-window
  recall estimate**. Those strata sit almost entirely outside the primary window
  and are weighted to their own populations, never to the cohort population.

## Sampling

- Deterministic seed **20260916**, sampling without replacement inside each
  stratum, members ordered by event id before the draw.
- **No stratification by cohort year.** Year-specific precision is not being
  estimated, and equal annual coverage would badly overweight thin cohorts such as
  2021.
- Strata are mutually exclusive and assigned in this priority order; once assigned
  to an earlier stratum an event cannot appear in a later one:

  1. prospective-only
  2. foreign-proceeding-only
  3. receivership-only
  4. subsidiary-only
  5. ambiguous resolved
  6. ambiguous unresolved
  7. mapped rules-positive Chapter 7, resolved
  8. mapped rules-positive Chapter 11, resolved

- Targets: 70 mapped Chapter 11 resolved; all mapped Chapter 7 resolved if ≤ 30,
  otherwise 30; 30 ambiguous resolved; 25 ambiguous unresolved; 20
  subsidiary-only; all receivership-only if ≤ 15; all prospective-only; all
  foreign-proceeding-only.
- Stratum population sizes, sample sizes and inclusion probabilities are stored
  with the draw so Wilson or exact intervals and population-weighted estimates can
  be computed later. Estimates must be weighted by stratum population; the raw
  sample is not self-weighting.
- Events outside every stratum (unmapped positives, positives with an unresolved
  date) are not sampled and are not represented by this holdout.

## Rules that bind what happens next

- **If this holdout exposes a new systematic defect and the classifier is changed
  using it, this holdout becomes development data and a new holdout must be drawn**
  from a frame that also excludes it. Repairing against this sample and then
  reporting it as validation is prohibited.
- **No Gate 2 until the holdout passes.** Gate 2 does not run on unvalidated
  labels.
- Human labels are recorded only after the packet is reviewed; none exist at the
  time of this pre-registration, and no labels are committed with it.

---

## Amendment 1 — one event per CIK (2026-09-16, before any adjudication)

**No human labels had been recorded when this amendment was made.** The packet had
been generated but not reviewed, and no `human_*` field had ever been filled in.
This is a pre-adjudication correction of the sampling design, not a response to any
observed result.

What prompted it:

1. **An arithmetic inconsistency in the first draw's report.** It stated 189
   sampled events, 183 distinct CIKs and "4 CIKs contributing 2 events each". Those
   cannot all be true: 189 events over 183 CIKs is six excess events, not four.
2. **Repeated CIKs were real.** Four CIKs supplied more than one sampled event:
   1322056 Protective Life Secured Trust 2005-7 (4 events, all ambiguous
   unresolved), 727346 Global Healthcare REIT (2, both receivership-only), 1119664
   Nortel Networks Ltd (2, one subsidiary-only and one ambiguous resolved, both
   dated 2009-01-14 with one docket between them), and 1443002 Lehman Mortgage
   Trust 2008-6 (2 ambiguous resolved, dated 2008-09-15 and 2008-10-03). Judged
   from pipeline metadata alone — the filings were deliberately not read, since
   reading them would expose holdout cases — none of these groups can be shown to
   be distinct bankruptcies, and the Nortel pair is almost certainly one event
   split by the merge rule.
3. **The design now requires at most one event per CIK across the entire holdout**,
   sampled without replacement at both event and CIK level. Repeated CIKs inside a
   holdout create dependent observations: several cases can turn on one registrant's
   text and one adjudication judgement, which understates the variance of any
   precision estimate computed from the sample.
4. **Receivership-only becomes 11 cases from 11 distinct CIKs.** That stratum holds
   12 eligible events but only 11 distinct CIKs, because both of CIK 727346's
   events are receivership-only. Since the stratum is take-all and already
   exhausted, the twelfth case cannot be replaced. For the secondary audit the
   stratum is therefore redefined as *all distinct eligible CIKs*: 11 reviewed
   cases from 11 CIKs. Every other stratum keeps its pre-registered target
   (prospective-only 2, foreign-proceeding-only 5, subsidiary-only 20, ambiguous
   resolved 30, ambiguous unresolved 25, mapped Chapter 7 resolved 25, mapped
   Chapter 11 resolved 70). Final sample size becomes **188**.
5. **The primary estimand is unchanged.** Precision of the 2012–2024 mapped
   positive labels rests on the mapped Chapter 11 and Chapter 7 strata, which hold
   166 events across 166 CIKs and 25 events across 25 CIKs — no CIK collisions at
   all, so their targets and weights are untouched by this amendment.

Draw rules under the amendment:

- Sampling seed stays **20260916**. Review order is randomised under a separate
  seed, **20260917**, so sampling and presentation order are plainly independent.
- Take-all strata (prospective-only, foreign-proceeding-only, receivership-only,
  mapped Chapter 7 resolved) claim their CIKs first, in that order, so a partially
  sampled stratum can never starve an exhaustive one. The remaining strata then
  draw in the protocol's priority order: subsidiary-only, ambiguous resolved,
  ambiguous unresolved, mapped Chapter 11 resolved. Only events whose CIK is still
  unused are eligible at each step.
- Where one CIK has several eligible events in the stratum being drawn, its
  representative event is chosen deterministically under the sampling seed before
  the stratum is sampled.
- Both the event population and the distinct-CIK population of every stratum are
  stored with the draw. Inclusion probabilities are CIK-level; weighted estimates
  must use the stratum populations recorded in `final_validation_sample.csv`.

---

## Amendment 2 — adjudication method changed to blinded AI (2026-09-16, after adjudication, before any classifier change)

This amendment records a **methodological deviation**, not a design improvement.
It is written after the 188 labels were frozen, so it cannot have shaped them.

1. **The original protocol planned independent human adjudication.** The
   "Adjudication" section above states that final labels are adjudicated by a
   human, not an LLM, and that no LLM verdict may be recorded as a final label.
   That plan was not carried out.
2. **The final review was instead performed as blinded AI adjudication.** All 188
   cases were labelled by an AI adjudicator (Claude Opus 5) reading only the
   blinded packet: opaque case id, registrant name, CIK, accession numbers, Item
   1.03 text, 8-K/A amendment text, nearby filing text.
3. **The blinding held.** The adjudicating model did not see the validation key,
   the classifier outputs, the automated dispositions, the automated petition
   dates, the sampling strata or any development annotation until all 188 labels
   had been frozen, hashed and committed at `0e81b6c`. The key was opened only
   after that commit.
4. **The adjudicator is not independent.** The same model developed the Stage 1–5
   classifier logic being evaluated. Blinding at review time does not remove that
   dependence: shared priors about how Item 1.03 language maps to debtor identity,
   chapter and petition date are exactly what the classifier encodes. This is
   therefore **not independent human ground truth**, and no result derived from it
   may be described as ground-truth accuracy.
5. **All reported validation results are classifier-to-AI-adjudicator agreement
   estimates.** They bound how often two systems built from the same reading of
   the label policy disagree. They do not bound how often either is wrong.
6. **No classifier changes were made using the holdout.** The two disputed mapped
   positives stand as counted validation errors. No Stage 6 rule was written from
   them and no holdout case became a regression fixture, so the rule in "Rules
   that bind what happens next" is not triggered and the holdout is not converted
   to development data.
7. **The holdout remains frozen.** Sample membership, the frozen adjudication and
   the packet hashes are unchanged.

The pre-registered independent human adjudication of this holdout remains
outstanding. Should it ever be performed, it runs against this same frozen sample
and packet, and its results supersede the agreement estimates reported here.

Results are reported in `FINAL_VALIDATION_REPORT.md`.
