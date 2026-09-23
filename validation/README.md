# Label validation

The classifier's labels were adjudicated twice against the same frozen 188-case
holdout. Both passes are published because the first bears on how much weight the
second carries.

## The headline

Classifier mapped-positive labels confirmed against the human reference:
**92 / 95 = 0.9684, Wilson 95% CI [0.9112, 0.9892]**. Full results in
[`RESULTS.md`](RESULTS.md); read [`PROVENANCE.md`](PROVENANCE.md) alongside it,
because the procedure was not in every respect the one the protocol envisaged.

## What is in this directory

| file | what it is |
|---|---|
| `HUMAN_VALIDATION_PROTOCOL.md` | the design, frozen before any reviewer saw a case |
| `HUMAN_VALIDATION_ANALYSIS_PLAN.md` | every metric, frozen before any result was opened |
| `AMENDMENT_01_EVIDENCE_BOUNDARY.md` | the no-outside-lookup rule, pre-review |
| `AMENDMENT_02_PROTOCOL_DEVIATIONS.md` | how a disclosed lookup is handled, pre-review |
| `REVIEWER_INSTRUCTIONS.md` | what reviewers were told, including the definitions |
| `RESULTS.md` | the Phase 2A results report |
| `PROVENANCE.md` | what the procedure actually was, including its deviations |
| `results.json`, `results.csv` | machine-readable results |
| `analyse_phase2a.py` | the analysis script |
| `PHASE1_VALIDATION_PROTOCOL.md`, `PHASE1_VALIDATION_REPORT.md` | the earlier AI-adjudication pass, as history |

## What is deliberately not published, and why

The documents above refer by name to files that are **not** in this repository:

- `reviewer_A_packet.csv`, `reviewer_B_packet.csv` and the blank forms
- the completed reviewer forms and the human-consensus file
- `sealed_key/`, containing `final_validation_sample.csv`,
  `final_ai_adjudication.csv` and the presentation-order map
- `disagreements.csv`, the per-case A-against-B judgement table
- reviewer identities and their independence attestations

Two reasons. **Reviewer privacy**: the forms carry individual reviewers'
judgements and free-text rationales, and no reviewer consented to publication.
**Holdout integrity**: publishing the packets and the answer key would burn a
frozen holdout that other work may want to reuse, and would let any future
adjudication be contaminated by this one.

Because of this, `analyse_phase2a.py` is published for inspection but **cannot be
run from this repository**: it verifies four input hashes that are not shipped and
exits rather than proceeding. The numbers it produced are in `results.json` and
`results.csv`, and every one is reproduced in `RESULTS.md` with its numerator and
denominator.

Requests for the withheld artifacts, for replication purposes, can be directed to
the author; release would depend on reviewer consent.

## Reviewer background is not documented

The protocol required no specific professional credential, only the ability to
read an Item 1.03 disclosure and distinguish Chapter 7 from Chapter 11, the
registrant from an affiliate, the petition date from the disclosure date, and an
initial filing from a conversion. It also said reviewer background would be
recorded generically for methodological transparency.

**That generic record was not in fact captured**, so no reviewer-background
statement appears here. The illustrative phrases in the protocol, such as
"practising insolvency attorney", are examples of the intended format and are
**not** descriptions of the reviewers who worked on this holdout. Nothing about
their training or occupation is asserted, because nothing was recorded, and
inferring it after the fact would be invention. Reviewer C's independence
attestation was obtained and is noted in `PROVENANCE.md`; it carries no
background detail.

A reader weighing the validation should treat reviewer expertise as
**undocumented**, alongside the other qualifications in `PROVENANCE.md`.

## The one thing to read if you read nothing else

The final human reference **equals Reviewer A's judgements**. Reviewer B was an
independent first-pass agreement check across all 188 cases, and Reviewer C
reviewed the 29 substantive disputes and selected Reviewer A for every disputed
field without case-specific rationales. **This is not a conventional
independently reasoned multi-reviewer consensus**, and the paper does not
describe it as one.
