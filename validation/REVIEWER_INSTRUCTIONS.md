# EDGAR-X — Reviewer Instructions

Thank you for adjudicating these cases. Please read this page fully before
opening your packet. It should take about ten minutes.

## What you are doing

You will read 188 short excerpts from US Securities and Exchange Commission
filings and answer six questions about each. Your judgements will be compared
against an automated classifier. You are the reference standard; the classifier
is the thing being measured.

**You are not checking the classifier's work.** You will not see what the
classifier decided, and you should not try to guess it. Answer only from the
text in front of you.

## Independence, and why it matters

Please confirm before you begin that you have **not**:

- worked on this classifier, its label policy or its benchmark;
- seen any classifier output, disposition or petition date from this project;
- seen any earlier adjudication of these cases;
- seen an answer key, sampling stratum or development note.

**Do not discuss any case with the other reviewer until both of you have
submitted your completed forms.** Order your cases differently from each other
deliberately; that is why your packets are shuffled.

If at any point you realise you have prior exposure to a case from this project,
flag it in the rationale field rather than withdrawing the answer.

## Your files

| file | what it is |
|---|---|
| `reviewer_X_packet.csv` | your 188 cases, one per row |
| `reviewer_X_form.csv` | the blank form to fill in, already keyed by case ID |

Fill in `reviewer_X_form.csv` and return it. Keep the case IDs exactly as given;
they are how the rows are matched afterwards.

Your packet contains, for each case: an opaque case ID, the registrant's name,
its CIK, the accession numbers, the Item 1.03 text, any amendment text, and
nearby filing text. That is the entire evidence base, and the question is always
what that supplied text establishes.

## The evidence boundary

**Adjudicate only from your own packet.** While working on these cases you must
not:

- search the web;
- search EDGAR, or open any filing not supplied in your packet;
- search PACER, a bankruptcy court docket, or any other court record;
- search for the company, the CIK or an accession number in any system;
- consult the EDGAR-X repository, its documentation, or any EDGAR-X paper or
  result;
- **use an AI assistant of any kind**, for any part of the task, including
  summarising a case or drafting a rationale;
- ask another person, whether the other reviewer, a colleague or anyone else.

Your packet has a CIK and accession numbers on every row, so looking them up is
the natural thing to do. Please do not. You and the other reviewer must judge the
**same frozen evidence**, captured as the filings stood on 2026-09-16. An outside
lookup would bring in later information, make the two of you non-comparable, and
could reach this project's own published answers.

The AI rule is not incidental. This study exists because an AI adjudicator was
used in place of independent human review; consulting one here would reproduce
the exact problem it is meant to correct.

**If you have already looked something up, or you recognise a case from
elsewhere, say so in the rationale field for that case.** Do not withdraw or
quietly change the answer. A disclosed lookup can be accounted for; an
undisclosed one cannot. There is no penalty.

What happens next is fixed in advance, so you are not deciding it and neither is
anyone else: your answer for that one case is set aside, the case is **not**
dropped from the study, and it is sent to a different reviewer who works from the
same packet. Your other answers stand, and you stay on the study. The deviation
is reported in the write-up. This is why disclosing costs you nothing and helps a
great deal.

This section is Amendment 1 to these instructions, adopted 2026-09-23 before any
reviewer saw a case. The full rationale is in
`AMENDMENT_01_EVIDENCE_BOUNDARY.md`.

## Definitions

These reproduce the project's frozen label policy. They are not new rules, and
they are the definitions your answers will be read against.

**Same-CIK debtor.** The CIK is the legal-registrant unit. The registrant counts
as a debtor only if that exact registrant is explicitly named as a debtor, or is
unambiguously inside the filing's own definition of the debtors. Corporate
parent-child relationships are **not** resolved: a parent is not a debtor merely
because its subsidiary filed, and a subsidiary is not a debtor merely because its
parent filed. If you cannot tell, answer "unclear" rather than inferring.

**Initial Chapter 7 or Chapter 11.** A positive is an initial US Chapter 7 or
Chapter 11 petition. Record the chapter of that initial filing.

**Chapter conversion.** A later conversion, most often Chapter 11 to Chapter 7,
is **not** a new bankruptcy and does **not** change the initial chapter. If the
text describes a conversion of an existing case, the initial chapter is the
original one. A motion or stated intent to convert is never a Chapter 7 event.

**Subsidiary-only filing.** If only subsidiaries or affiliates filed, and the
registrant itself is not among the debtors, the registrant is **not** a debtor.
Answer "No" to question A and "subsidiary/affiliate only" to question D.

**Foreign insolvency.** A foreign proceeding on its own is **not** a US Chapter 7
or Chapter 11 filing. This includes Canadian CCAA and BIA proceedings, UK
administration, Dutch *surseance van betaling* and German *Insolvenzverfahren*.
If a registrant is in a foreign proceeding and no US Chapter 7 or 11 petition by
that registrant is described, answer "No" to question A, and say so in the
rationale.

**Receivership.** Receivership alone is not a Chapter 7 or Chapter 11 filing.
The same applies to conservatorship and to an assignment for the benefit of
creditors.

**Petition date.** The date the petition was filed with the bankruptcy court.
This is **not** the date of the 8-K, the date of the press release, or the
"report date" on the filing header. In an involuntary bankruptcy it is the date
the petition was filed against the debtor, not the later order-for-relief date.
**Never fall back to the 8-K date.** If the filing does not state the petition
date, answer "cannot determine".

**Amendment correction.** Where an 8-K/A explicitly corrects an earlier petition
date, the corrected date is the right answer. Amendment text, where it exists, is
in your packet.

**Prospective intent.** Board authorisation to file, preparation to file, a
stated intention to file, or an explicit negation such as "the Company has not
filed" are **not** bankruptcies. Answer "No" to question A.

## The six questions

**A. Is the exact SEC registrant identified by this CIK itself a debtor in an
initial US Chapter 7 or Chapter 11 proceeding?**
`Yes` / `No` / `Cannot determine from supplied evidence`

*Answer only for the registrant named by that CIK, not for its corporate group.*

If and only if you answered **Yes**:

**B. Initial chapter.** `Chapter 7` / `Chapter 11` / `Cannot determine`

**C. Petition date.** An exact date as `YYYY-MM-DD`, or `cannot determine`.

Always answer C, D, E and F:

**D. Identity assessment.**
`exact registrant is debtor` / `subsidiary/affiliate only` / `parent/other entity only` / `unclear`

**E. Evidence confidence.** `high` / `moderate` / `low`

*Descriptive only. A low-confidence answer is still your answer, and it will not
be discarded. Please do not inflate or deflate it to signal anything.*

**F. Short rationale.** One or two sentences pointing to the text that supports
your judgement. Quote or paraphrase the decisive phrase. This is the most useful
field when the two of you disagree, so please complete it on every case,
including the easy ones.

## "Cannot determine" is a real answer

It is a substantive finding, not a failure. If the supplied evidence genuinely
does not settle the question, say so. Two reviewers both answering "cannot
determine" counts as agreement. Please use it rather than guessing.

## If you disagree

You will not know whether you disagree until both forms are in. Where the two of
you differ on disposition, debtor identity, chapter or petition date, that case
goes to a third independent reviewer who sees the same evidence and both of your
judgements. Nothing you write will be edited.

## Returning your work

Return the completed `reviewer_X_form.csv` with all 188 rows. Please do not
alter the case IDs, add or remove rows, or reorder them.
