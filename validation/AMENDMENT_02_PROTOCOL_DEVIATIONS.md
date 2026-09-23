# Amendment 2 — External-Lookup Protocol Deviations

**Adopted 2026-09-23, before any reviewer has received a packet.**
Amends: `../HUMAN_VALIDATION_ANALYSIS_PLAN.md`, `../HUMAN_VALIDATION_PROTOCOL.md`,
`AMENDMENT_01_EVIDENCE_BOUNDARY.md`, `REVIEWER_INSTRUCTIONS.md`.

## Why this amendment exists

Amendment 1 established the evidence boundary and told reviewers to disclose a
prohibited lookup in the rationale field rather than withdraw the answer. It said
a disclosed lookup "can be reported and excluded in analysis" without saying
which analyses exclude it, whether the whole case or one judgement is affected,
how consensus is then reached, or what happens to inter-reviewer agreement.

Leaving that undefined would let the handling be chosen after seeing which cases
were contaminated, which is precisely the discretion this study is designed to
remove. The rule below is therefore fixed now, before any reviewer has seen a
case and before any deviation is known to exist.

## Definitions

**Prohibited external source.** Any source outside the reviewer's own frozen
packet, as enumerated in Amendment 1: the web; EDGAR or any filing not in the
packet; PACER, a bankruptcy docket or any court record; a search on company name,
CIK or accession number; the EDGAR-X repository, documentation, papers or
results; an AI assistant of any kind; another person.

**Reviewer-case judgement.** One reviewer's set of answers for one case. It is
the unit that becomes contaminated, not the case and not the reviewer.

**Protocol-contaminated.** A reviewer-case judgement for which the reviewer
disclosed use of a prohibited external source, or for which such use is otherwise
established.

## The rule

1. **A disclosed external lookup contaminates that reviewer's judgement for that
   case only.** The reviewer's other 187 judgements are unaffected, and the
   reviewer is not removed from the study.

2. **The case is not dropped.** All 188 cases remain in the validation sample.
   The frozen sample is not re-drawn, re-weighted or reduced.

3. **The contaminated judgement is excluded from Reviewer A against Reviewer B
   first-pass agreement and from Cohen's kappa, for that case only.** This is
   pairwise deletion: the agreement and kappa denominators fall by the number of
   affected cases, and **both the reduced denominator and the number excluded are
   reported alongside every affected statistic.**

4. **A contaminated judgement cannot establish final human consensus.** It is
   never one of the two agreeing judgements, and it is never shown to the
   adjudicating reviewer.

5. **The affected case is independently re-reviewed by a fresh eligible human
   reviewer**, using only the frozen evidence packet for that case and the same
   questionnaire. The replacement reviewer meets the eligibility conditions in
   §4 of the protocol in full.

6. **The replacement reviewer must not see** the contaminated judgement, the
   other first-pass judgement, classifier output, the AI adjudication, any
   answer-key field, or the sampling stratum.

7. **Once an uncontaminated replacement judgement exists, the normal consensus
   and adjudication rule applies**, using only uncontaminated judgements: the
   replacement judgement takes the contaminated one's place as a first-pass
   judgement, and if it and the surviving first-pass judgement disagree on
   disposition, debtor identity, chapter or petition date, the case goes to the
   third adjudicating reviewer as usual.

8. **Reporting.** The human validation report states:
   - the number of contaminated reviewer-case judgements;
   - the number of affected cases;
   - the cause of each deviation, from the reviewer's own disclosure;
   - **whether any primary mapped-positive case was affected**, and if so which,
     since the primary quantity is computed on those cases;
   - the reduced denominators used for first-pass agreement and kappa.

9. **Nothing is silently deleted or replaced.** The contaminated judgement is
   retained in the committed reviewer files, flagged rather than removed, so the
   deviation and its replacement remain auditable. A reader must be able to
   reconstruct both the contaminated and the corrected analysis.

## Cases the rule must also cover

Fixed now so none of them becomes a judgement call later.

**Both first-pass reviewers contaminated on the same case.** Two replacement
judgements are obtained, from two different fresh eligible reviewers. The case
contributes nothing to first-pass agreement or kappa and is counted once in the
excluded denominator.

**The adjudicating reviewer contaminated on a disputed case.** That adjudication
is void. A different fresh eligible adjudicator resolves the case, seeing the
evidence and the two uncontaminated first-pass judgements, and not the void
adjudication.

**A replacement reviewer discloses a lookup.** The rule applies again to that
judgement. **Stopping rule: after two replacement attempts for the same
reviewer-case slot, the case is reported as unresolvable under protocol** and
carried in a separate "protocol-unresolved" category. It is still not dropped
from the sample, and it counts as not confirmed in the primary quantity, matching
the conservative treatment already fixed for "cannot determine".

**Disclosure arrives after the form is submitted.** It is honoured whenever it
arrives, up to the point the analysis is frozen. A disclosure arriving after the
analysis freeze is reported as a post-freeze deviation and the analysis is not
silently re-run.

**Suspected but undisclosed contamination.** No judgement is treated as
contaminated on suspicion alone. Only a disclosure, or independently established
use, triggers this rule. A reviewer's answer is never discarded for being
inconvenient, unexpected, or merely different from the classifier.

## What this amendment does not change

No reviewer packet, blank form, evidence field, case ID, presentation order,
questionnaire item, primary metric definition or frozen sample is altered. The
188 cases and both presentation orders are byte-identical to the freeze at commit
`631a19768ceb6f65cc95d787970554b9461177bc`.
