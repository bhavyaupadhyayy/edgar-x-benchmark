# Amendment 1 — Reviewer Evidence Boundary

**Adopted 2026-09-23, before any reviewer has seen a case.**
Amends: `human_validation/REVIEWER_INSTRUCTIONS.md`.
Governed by: `../HUMAN_VALIDATION_PROTOCOL.md`.

## Why this amendment exists

The instructions as first frozen said only:

> That is the entire evidence base. **Please do not look up court records, news
> or other outside sources.** The question is what the supplied filing text
> establishes.

That names court records and news and then relies on the catch-all "other
outside sources". It is a request rather than a requirement, and it leaves four
routes unnamed that a reviewer could take in good faith:

1. **Searching EDGAR.** Every packet row hands the reviewer a CIK and accession
   numbers. Looking them up is the most natural thing a careful person would do,
   and nothing in the original wording told them not to.
2. **A general web search** on the registrant's name.
3. **An AI assistant.** Not mentioned at all.
4. **Asking another person.** Only the *other reviewer* was out of bounds; a
   colleague or a subject-matter friend was not.

## What changes

Nothing about the study except the wording of the instruction. **No packet,
label, evidence field, questionnaire item, statistical quantity or reviewer-order
seed is altered.** The 188 cases, their evidence, their opaque IDs and both
presentation orders are byte-identical to the freeze at commit
`631a19768ceb6f65cc95d787970554b9461177bc`.

## The rule, stated in full

A first-pass reviewer must adjudicate **only** from the evidence supplied in
their own frozen packet. While working on these cases they must not:

- search the web;
- search EDGAR, or open any filing not supplied in the packet;
- search PACER, a bankruptcy court docket, or any other court record;
- search for the company, the CIK or an accession number in any system;
- consult the EDGAR-X repository, its documentation, or any EDGAR-X paper or
  result;
- use an AI assistant of any kind, for any part of the task, including
  summarising a case or drafting a rationale;
- ask another person, whether the other reviewer, a colleague or anyone else.

## Why the boundary is this strict

Reviewer A and Reviewer B must evaluate **the same frozen evidence set**. The
packets were frozen from filings as they stood at the 2026-09-16 sample freeze.
Any outside lookup would:

- introduce information published after the freeze, so the two reviewers would
  no longer be answering the same question;
- make the two reviewers non-comparable, since they would not have searched the
  same things, which would corrupt the reviewer-reviewer agreement and Cohen's
  kappa defined in the analysis plan;
- risk reaching EDGAR-X's own published material, which carries the classifier's
  answers and the earlier AI adjudication, destroying the blinding this study
  exists to establish.

The AI prohibition is not incidental. This study exists because an AI adjudicator
was substituted for independent human review in Phase 1. A reviewer who consults
an AI would reintroduce exactly the correlated-error problem being corrected, and
the resulting labels would not be an independent reference standard.

## If the boundary is crossed

A reviewer who has already looked something up, or who recognises a case from
outside this packet, **should say so in the rationale field for that case rather
than withdrawing or silently correcting the answer.** Disclosure is more useful
than a clean-looking form: a disclosed lookup can be handled openly, an
undisclosed one cannot. There is no penalty.

**What happens to a disclosed lookup is fixed in
`AMENDMENT_02_PROTOCOL_DEVIATIONS.md`**, adopted 2026-09-23 before any reviewer
received a packet. In outline: that one judgement is set aside, the case is not
dropped, the case is independently re-reviewed by a fresh reviewer, and the
deviation is reported. Nothing is deleted and the reviewer is not removed from
the study.

## Scope

This amendment binds the two first-pass reviewers, A and B, and the third
adjudicating reviewer, C. Reviewer C additionally sees the two first-pass
judgements for disputed cases, as the protocol already provides, and remains
bound by every other clause above.
