# Final Validation Report — 188-case untouched holdout

> **Historical document, superseded in part.** This records the *first*
> validation pass, which used a blinded AI adjudicator. An independent human
> adjudication of the same frozen holdout was completed afterwards and is the
> evidence the working paper relies on; see `RESULTS.md`, `PROVENANCE.md` and
> `HUMAN_VALIDATION_PROTOCOL.md` in this directory. Statements below about
> human adjudication being outstanding were true when written and are no longer
> current. Nothing here has been edited.

**Date:** 2026-09-16
**Adjudication commit (frozen before the key was opened):** `0e81b6c`
**Method:** blinded AI adjudication (see Amendment 2 of `FINAL_VALIDATION_PROTOCOL.md`)

---

## 1. Methodological deviation — read this before any number

The original protocol planned **independent human adjudication** of this holdout.
That is not what happened.

- The final review was performed as **blinded AI adjudication**. All 188 cases
  were labelled by an AI adjudicator (Claude Opus 5) from the blinded packet only:
  opaque case id, registrant name, CIK, accession numbers, Item 1.03 text, 8-K/A
  amendment text, nearby filing text.
- **The blinding held.** The adjudicating model did not see the validation key,
  the classifier outputs, the automated dispositions, the automated petition
  dates, the sampling strata or any development annotation until all 188 labels
  had been frozen, hashed and committed at `0e81b6c`. `final_human_review_key.csv`
  was opened only after that commit.
- **The adjudicator is not independent of the classifier.** The same model
  developed the Stage 1–5 classifier logic under evaluation. Blinding at review
  time does not remove that dependence — shared priors about how Item 1.03
  language maps to debtor identity, chapter and petition date are precisely what
  the classifier encodes.
- **Therefore every figure below is a classifier-to-AI-adjudicator agreement
  estimate.** These are *AI-adjudicated validation results*, not ground-truth
  accuracy. They bound how often two systems built from the same reading of the
  label policy disagree with each other. They do not bound how often either is
  wrong. Correlated error is not merely possible here; it is the expected failure
  mode, and it biases these agreement figures **upward** by an unknown amount.
- **No classifier changes were made using this holdout.** The two disputed mapped
  positives remain counted as validation errors. No Stage 6 rule was derived from
  them; no holdout case became a regression fixture.
- **The holdout remains frozen.** Sample membership, the adjudication file and the
  packet hashes are unchanged.

The pre-registered independent human adjudication remains outstanding. If it is
ever performed, it runs against this same frozen sample and packet and its results
supersede everything below.

---

## 2. Primary estimand — 2012–2024 mapped positive labels

Pre-registered as the precision of the mapped positive labels; reported here as
the rate at which the AI adjudicator confirms them.

| Quantity | Value |
|---|---|
| Mapped positive cases drawn | **95** (one per CIK, cohorts 2012–2024) |
| Confirmed by adjudicator | **93** |
| Disputed | **2** |
| Unweighted agreement / precision-style estimate | **0.9789** |
| Wilson 95% CI | **[0.9265, 0.9942]** |
| CIK-weighted estimate (inverse inclusion probability) | **0.9823** |
| Chapter 11 stratum | **69/70** (CI [0.9234, 0.9975]) |
| Chapter 7 stratum | **24/25** (CI [0.8046, 0.9929]) |
| Chapter agreement among confirmed positives | **93/93** |
| Petition-date exact agreement among confirmed positives | **93/93** |

Among the 93 confirmed positives, neither side left a petition date unresolved,
and every date matched exactly. Cohort spread of the 95 drawn cases: 2012→4,
2013→2, 2014→5, 2015→12, 2016→7, 2017→6, 2018→4, 2019→12, 2020→8, 2021→1,
2022→9, 2023→13, 2024→12.

### The two disputed positives (counted as errors, deliberately unrepaired)

Both are debtor-identity calls, both carry the adjudicator's high confidence, and
both sit on the exact patterns Stage 5 was built to handle.

**`V-918b6e0e42`** — CIK 1660719, 2018 cohort. Automated: `registrant_chapter_11`,
petition date 2018-08-10. Adjudicator: the registrant is a **CCAA** debtor in
Canada; the chapter 11 petitions were filed by its US and Irish subsidiaries, not
by the registrant. Under `LABEL_POLICY.md` a foreign proceeding alone is not a
positive, so this reads as a genuine false positive: a CCAA commencement sentence
naming the registrant sits in the same paragraph as the subsidiaries' chapter 11
filing sentence.

**`V-7d9988c4d9`** — CIK 1496818, 2019 cohort. Automated: `registrant_chapter_7`,
petition date 2020-01-27. Adjudicator: the chapter 7 debtor is a **Florida
subsidiary bearing the registrant's exact name**, while the registrant is the
Nevada parent, which did not petition. Point-in-time naming cannot resolve this,
because the two entities' names are character-identical; only the state of
incorporation and the explicit "wholly owned subsidiary" apposition separate them.

One additional flag inside the confirmed set: **`V-4e2be84dcf`** (CIK 1592058).
Debtor, chapter and the 2023-01-17 date all agree, but the adjudicator reads this
particular 8-K as a plan-confirmation update rather than the initial petition
report. Event-level classification is unaffected.

---

## 3. Secondary error audit — not an in-window recall estimate

Per the protocol, the non-positive strata are a classifier-error audit drawn from
the broader untouched population. They sit almost entirely outside 2012–2024 and
**cannot** be read as ambiguous-bucket recall inside the primary window.

| Stratum | n | Adjudicator says registrant Ch7/11 | 95% CI |
|---|---|---|---|
| ambiguous resolved | 30 | 7 (0.233) | [0.118, 0.409] |
| ambiguous unresolved | 25 | 5 (0.200) | [0.089, 0.391] |
| foreign-proceeding-only | 5 | 1 (0.200) | [0.036, 0.624] |
| subsidiary-only | 20 | 0 | [0.000, 0.161] |
| receivership-only | 11 | 0 | [0.000, 0.259] |
| prospective-only | 2 | 0 | [0.000, 0.658] |

Clean directions: in this sample the classifier never mistook a subsidiary-only,
receivership-only or prospective-only case for a registrant filing.

### Docket-clustering limitation

**The ambiguous-stratum rates above are not independent observations.** Six of the
seven "ambiguous resolved" hits are six separate PDC Energy limited partnerships
— CIKs 1080504, 1093942, 1127358, 1127362, 1156221, 1224923 — that are all named
debtors in **one bankruptcy docket, 13-34773**, each reporting the same
2013-09-16 petition and the same plan confirmation. That is one classifier
behaviour sampled six times, not six independent errors.

The one-event-per-CIK amendment removed within-sample *CIK* dependence; it does
not remove within-*docket* dependence, because six distinct registrants can share
a single bankruptcy. Any confidence interval computed on the ambiguous strata as
if the draws were independent is therefore too narrow. Excluding the cluster, the
residual is one ambiguous-resolved case (`V-103e0e4918`, registrant chapter 7,
2008-05-30), five ambiguous-unresolved cases and one foreign-proceeding case —
most of them Item 1.03 bodies that are pure cross-references, where the petition
date is genuinely absent from the text the adjudicator was given.

This limitation does **not** touch the primary estimand: the mapped Chapter 11 and
Chapter 7 strata contributed 95 cases across 95 CIKs, and the two disputed cases
sit in different dockets, different years and different chapters.

---

## 4. Uncertainty and coverage

- Adjudicator confidence across all 188: high 157, medium 30, low 1. Both disputed
  positives are high-confidence. Two of the 95 mapped positives carry medium
  confidence; both were confirmed.
- Two cases were unadjudicable from the packet text and are labelled `unclear`:
  `V-a71d55a841` (auto-generated paper-submission placeholder, no disclosure) and
  `V-ffd430d1c3` (Item 1.03 body is the bare word "RECEIVERSHIP"). Neither is in
  the primary estimand.
- 28 of 188 cases have `ai_petition_date = unresolved`; none is a confirmed
  positive.
- Four FDIC bank-receivership rows were re-scored by rule before freezing, so that
  identical fact patterns received identical labels; documented in
  `FINAL_AI_ADJUDICATION_PROVENANCE.md`. None is in the primary estimand.
- The Chapter 7 interval is wide (n=25): the single disputed Ch7 case moves the
  point estimate by roughly four percentage points.
- The agreement estimates are upward-biased by the non-independence described in
  §1. No correction is applied, because the magnitude is not estimable from this
  sample.

---

## 5. Status

- Classifier: **frozen**. Stages 1–5 unchanged; no Stage 6.
- Holdout: **frozen and spent** for this version of the benchmark. Not converted
  to development data.
- Disputed positives: **counted as errors**, unrepaired.
- Gate 2: may proceed on these AI-adjudicated labels, with the agreement-not-
  accuracy framing carried into every downstream claim.

## 6. Artifacts

| File | SHA-256 |
|---|---|
| `final_ai_adjudication.csv` | `58dac26867f0ba63477dd3ac986b3a023dc0fb389fd2202bbcc23f7211d10737` |
| `FINAL_AI_ADJUDICATION_PROVENANCE.md` | `207156fc916298d55864473764d78623fd2bbb355d189d569d3316d1b567eeb2` |
| `final_validation_sample.csv` | `9517647b14d84ef2cfcc66b34e6294beeed1132b59cea9717666ffcd7f537c50` |
| `final_human_review_packet.csv` (untracked, local) | `b27ed86c084bc390695b7f34a4eb0bf866addee9b1f93b3aa52fc635315a5532` |
| `final_human_review_packet.md` (untracked, local) | `1573b8994c6835ddc236a95688352c575ec4dd5ede571f3928b515af3bc55cba` |

Supporting: `FINAL_VALIDATION_PROTOCOL.md` (design + Amendments 1 and 2),
`final_validation_sampling_log.txt` (draw, integrity checks, hashes),
`final_human_review_key.csv` (strata, inclusion probabilities, automated labels).
