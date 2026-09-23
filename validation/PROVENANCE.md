# Phase 2A — Provenance and Procedure

Read this before the results. It records what the procedure actually was, which
is not in every respect what the frozen protocol envisaged.

## Artifacts and their authority

| role | file | SHA-256 |
|---|---|---|
| Reviewer A, authoritative final submission | `inputs/reviewer_A_authoritative.csv` | `6588e557…0d3b1cf0` |
| Reviewer B, authoritative raw submission | `inputs/reviewer_B_authoritative.csv` | `3da0bbe5…4efc566a` |
| Reviewer C, transcribed adjudication | `inputs/reviewer_C_form_completed_transcribed.csv` | `4ca9e644…e5418881` |
| Final human consensus | `inputs/human_consensus_188.csv` | `49fa6293…ac9713377` |

All four were supplied and hash-pinned by the project author. Each was verified
against its declared hash before use and copied into this package unmodified. The
analysis script re-verifies all four hashes on every run and exits non-zero on
mismatch.

## What Reviewer C actually did

Reviewer C received the 29 cases carrying substantive A/B disagreements, provided
the required independence attestation, and **explicitly selected Reviewer A's
judgment for every disputed field**. Reviewer C did **not** write 29 separate
case-specific rationales.

`reviewer_C_form_completed_transcribed.csv` is therefore a transparent
transcription of that single blanket decision onto 29 rows. The identical
rationale string on every row is a transcription artifact, not 29 independent
written judgements. **Nothing in this package should be read as claiming that
Reviewer C individually reasoned each case in writing.**

## What that means for the reference standard

Because Reviewer C selected Reviewer A on every disputed field, the final human
consensus **equals Reviewer A's authoritative adjudication exactly**. The
analysis verifies this directly: consensus matches Reviewer A on 188 of 188 cases
for all four fields, with zero mismatches.

The reference standard for Phase 2A is therefore, in substance, **one human
reviewer's judgement (Reviewer A), ratified wholesale by a second independent
human (Reviewer C), with a third (Reviewer B) serving as an independent agreement
check.** It is not a two-reviewer consensus in which each disputed case was
independently re-reasoned.

This is a meaningful improvement on Phase 1, where the adjudicator was an AI
system that had been involved in developing the classifier it reviewed. It is
weaker than the design the frozen protocol described. Both statements are true
and both are reported.

## Reviewer B artifact naming

The Reviewer B file supplied as authoritative is named
`reviewer_B_form_reconstructed.csv`, and the Reviewer A file
`reviewer_A_form_corrected (1).csv`; two other non-matching Reviewer A variants
exist alongside it. The authoritative hashes disambiguate which files are in
force, and only those were used. The project author should record, for the
eventual write-up, what "reconstructed" and "corrected" refer to, since a reader
will reasonably ask whether the first-pass submissions were edited after
collection. **That question is not answerable from the artifacts alone and is not
answered here.**

## Deviations from the frozen protocol

1. **Reviewer C gave a blanket rather than case-by-case adjudication.** Protocol
   §6 has C adjudicate each disputed field on the evidence. A single "select A
   throughout" decision satisfies the letter but supplies no per-case reasoning,
   so per-case independence cannot be verified from the record.

2. **23 of 52 field-level disagreements were not routed to Reviewer C.** In all
   23, both reviewers answered "No" to disposition, so the chapter question was
   not applicable; Reviewer A left it blank and Reviewer B wrote "Cannot
   determine". That is an encoding difference, not a substantive disagreement.
   The frozen analysis plan defined disagreement field-by-field with **no
   not-applicable carve-out**, so treating these as non-substantive is a
   **post-hoc refinement**. Both counts are reported throughout: 52 literal
   field-level disagreements, 29 substantive.

3. **No external-lookup deviations.** Amendment 2's contamination rule was
   scanned for and found zero disclosed lookups in either reviewer's rationales.
   No reviewer-case judgement was excluded, no case was re-reviewed, and no
   denominator was reduced on that account.

## What was not done

No benchmark model was run. No Phase 1 label was changed. No case was dropped,
re-drawn, re-weighted or substituted; all 188 frozen `case_id`s are present and
match the committed packet. No population accuracy, sensitivity, specificity,
recall or prevalence was estimated from this stratified sample. The AI
adjudication was not treated as ground truth. Working paper v1 is untouched.
