# EDGAR-X — Independent Human Adjudication Protocol (Phase 2A)

**Status:** frozen 2026-09-23, before any human reviewer has seen a case.
**Design:** independent follow-up validation study on a previously frozen holdout.

This is **not** a new model experiment and **not** a new sample. It re-adjudicates
the same 188-case holdout that was frozen on 2026-09-16 and reported in
`FINAL_VALIDATION_REPORT.md`, this time with independent human reviewers rather
than the blinded AI adjudicator that was actually used.

## 1. Why this study exists

The frozen protocol `FINAL_VALIDATION_PROTOCOL.md` specified independent human
adjudication. That is not what happened: all 188 cases were adjudicated by a
blinded AI adjudicator that had also been involved in developing the classifier
it reviewed (Amendment 2 of that protocol). Every figure in
`FINAL_VALIDATION_REPORT.md`, and every validation figure in working paper v1,
is therefore a **classifier-to-AI-adjudicator agreement estimate**, biased upward
by correlated error in an unquantified way.

Phase 2A exists to replace that limitation with a measurement whose reference
standard is independent of the system under review.

## 2. What is frozen and must not change

The Phase 1 empirical freeze is immutable. This study does not alter classifier
rules, benchmark labels, event construction, model outputs, cohort membership,
feature arms, predictions or bootstrap results. Working paper v1
(`e59e777eaddc77735513c7684e66eb6250146bfd`, PDF SHA-256
`56d30d214bb4e48e3317fac44a0a954d1007e4af74fd894102932a5db48e288c`) is not
edited. Any revision arising from this study becomes a **later paper version**,
never an overwrite of v1.

## 3. The holdout is reused exactly

| property | value |
|---|---|
| cases | 188 |
| distinct CIKs | 188 (one event per CIK) |
| overlap with `DEV_EXPOSURE_REGISTRY.csv` (1,212 CIKs) | **0** |
| original sampling seed | 20260916 |
| original review-order seed | 20260917 |
| source of evidence | `final_human_review_packet.csv`, frozen 2026-09-16 |
| answer fields in that source | all blank, verified before build |

No case was redrawn, resampled, rebalanced or substituted. The opaque case IDs
(`V-` plus a ten-character digest) are carried over verbatim, so every case in
this study maps one-to-one onto the case the AI adjudicator saw.

**Presentation order is re-randomised per reviewer**, under seeds fixed here
before any review: **Reviewer A = 20260923, Reviewer B = 20260924**. The
resulting mapping is written to `human_validation/sealed_key/presentation_order_map.csv`
and sealed now, so order effects cannot be tuned after the fact and the two
reviewers cannot align their work by row number.

## 4. Reviewer independence

A reviewer is eligible only if they have **not**:

- participated in developing the classifier, the label policy or the benchmark;
- seen any classifier label, disposition or petition date;
- seen the AI adjudication results;
- seen the answer key;
- seen the sampling strata or inclusion probabilities;
- seen any development annotation.

**Bhavya Upadhyay must not adjudicate**, having developed the project.

**No AI system may serve as a reviewer or as a disagreement resolver.** This
includes Claude, ChatGPT and any other model. The failure this study corrects is
precisely the substitution of an AI adjudicator for an independent human one;
repeating it in the resolution step would void the study.

Reviewers confirm eligibility in writing before receiving a packet. The
confirmations are retained; reviewer identities are not published without
consent.

### Qualifications

No specific professional credential is required. A reviewer must be able to read
an SEC Form 8-K Item 1.03 disclosure and distinguish:

- Chapter 7 from Chapter 11;
- the registrant from an affiliate or subsidiary;
- the petition date from the disclosure or report date;
- an initial filing from a chapter conversion.

Reviewer background is recorded generically for methodological transparency, for
example "practising insolvency attorney" or "accounting researcher, no role in
this project", without private identifying detail unless the reviewer consents.

## 5. Design

Two independent human reviewers, **A** and **B**, each label all 188 cases.

- Reviewers work from identical evidence in different presentation orders.
- **Reviewers must not communicate before both first-pass label sets are frozen.**
- First-pass label sets are hashed and committed on receipt, before any
  comparison is run.

Where A and B disagree on the **primary disposition, debtor identity, chapter or
petition date**, only those disputed cases go to a third independent human
adjudicator, **C**.

- C sees the original evidence and the two first-pass judgements.
- C does **not** see the automated disposition, the automated petition date or
  the AI adjudication.
- C's adjudicated value becomes final **for the disputed field only**; undisputed
  fields on the same case keep the A/B consensus.

## 6. Consensus rule (frozen)

1. A and B agree on a field → that value is the final human value.
2. A and B disagree on disposition, debtor identity, chapter or petition date →
   C adjudicates that field, and C's value is final.
3. "Cannot determine" is a substantive answer, not a missing value. Two reviewers
   both answering "cannot determine" is agreement, and the final human value is
   "cannot determine".
4. Bhavya Upadhyay does not resolve disagreements.
5. No AI system resolves disagreements.

## 7. What reviewers receive

Only `human_validation/REVIEWER_INSTRUCTIONS.md`, their own
`reviewer_X_packet.csv` and their own blank `reviewer_X_form.csv`. Each packet
row carries exactly: presentation order, opaque case ID, registrant name, CIK,
accession numbers, Item 1.03 text, amendment text where one exists, and nearby
filing text. Nearby filing text is included because the frozen protocol already
allowed it.

Reviewers never receive `human_validation/sealed_key/`, the frozen result
documents, the validation report, the working paper, or any file in this
repository outside their own packet, form and instructions.

## 8. The benchmark is not corrected by this study

Human adjudication is used **for validation only**. Benchmark labels are not
changed on the strength of these results. If the reviewers identify label errors,
those are reported as validation findings.

Any subsequent correction must be a separately declared, versioned dataset
update with its own freeze, and must not silently rewrite the Phase 1 empirical
freeze. The two label errors already known from Phase 1 (the CCAA case and the
same-name-subsidiary case) remain in the benchmark and remain disclosed.

## 9. Analysis

Every metric is fixed in `HUMAN_VALIDATION_ANALYSIS_PLAN.md`, frozen at the same
time as this protocol and before any reviewer result is opened.

## 10. Amendments

**Amendment 1, adopted 2026-09-23, before any reviewer saw a case: reviewer
evidence boundary.** The instructions as first frozen asked reviewers not to look
up "court records, news or other outside sources". That catch-all left four
routes unnamed: searching EDGAR (the packet supplies a CIK and accession numbers
on every row), a general web search, using an AI assistant, and asking a person
other than the other reviewer. The rule is now enumerated in full in
`human_validation/AMENDMENT_01_EVIDENCE_BOUNDARY.md` and restated in the
reviewers' own instructions. A reviewer who has already looked something up
discloses it in the rationale field rather than withdrawing the answer.

No packet, label, evidence field, questionnaire item, statistical quantity or
reviewer-order seed was altered by this amendment; the reviewer packets and forms
are byte-identical to the original freeze.

**Amendment 2, adopted 2026-09-23, before any reviewer received a packet:
external-lookup deviation handling.** Amendment 1 told reviewers to disclose a
prohibited lookup but did not say what happens to the disclosed judgement.
`human_validation/AMENDMENT_02_PROTOCOL_DEVIATIONS.md` now fixes it: the
disclosed reviewer-case judgement is protocol-contaminated; the case stays in the
sample; the judgement is excluded pairwise from first-pass agreement and kappa
and cannot establish consensus; the case is independently re-reviewed by a fresh
eligible reviewer blinded to the contaminated judgement, the classifier, the AI
adjudication, the key and the stratum; the normal consensus rule then applies to
uncontaminated judgements only; and everything is reported and retained rather
than deleted. No packet, form, evidence field, case ID, presentation order,
questionnaire item, primary metric or frozen sample changed.

## 11. Stop condition for this commit

This commit contains the protocol, the analysis plan, the reviewer instructions,
the blinded packets, the blank forms, the sealed key and the hashes. **It
contains no reviewer answers, because none exist.**
