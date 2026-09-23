# EDGAR-X — Data Card

**Version:** frozen at `dcee1037bcb21e358be531d988e147fd7641e696`
**Window:** 2012–2024 · **Jurisdiction:** United States · **Language:** English

---

## What EDGAR-X is

A **point-in-time benchmark for predicting corporate bankruptcy from SEC
filings**. Each observation is one Form 10-K; the label is whether the same
registrant filed an initial US Chapter 7 or Chapter 11 petition within 365 days
of that filing's EDGAR acceptance timestamp.

The defining property is that **every input is reconstructed as it existed at
prediction time**. Financial facts are as-filed, not restated. Industry codes are
those carried on the filing. Identity is the CIK on the document. The event time
is the actual petition date, not its disclosure date.

| quantity | value |
|---|---|
| observations (2012–2024) | **59,500** |
| positives | **437** |
| prevalence | **0.7345%** |
| rolling-testable (2013–2024) | **54,351** observations / **408** positives |
| distinct CIKs | 9,586 |
| Item 1.03 filings processed | 3,786 |
| assembled bankruptcy events | 3,010 |
| 10-K primary documents retrieved | 59,499 |

## Exact bankruptcy definition

An observation is **positive** if the registrant identified by the same **CIK**
filed an **initial** petition for relief under **Chapter 7 or Chapter 11 of the
US Bankruptcy Code** with a **petition date strictly within 365 days after** the
10-K's EDGAR acceptance timestamp.

Explicitly **not** positive on their own:

- receivership, conservatorship (including FDIC and FHFA appointments);
- assignment for the benefit of creditors and other state-law liquidations;
- foreign proceedings — CCAA, UK administration, Irish winding-up, Chapter 15
  recognition;
- a **subsidiary's or affiliate's** petition where the registrant is not itself
  demonstrably among the debtors;
- **prospective** filings: board authorisation, preparation, or a stated
  intention to file;
- **conversion** between chapters, which is not a new initial event.

Where identity or chapter cannot be resolved from the filing text, the event is
recorded as **ambiguous** and retained as an upper-bound case rather than forced
into a bucket. Where a petition date cannot be resolved, the event is **dropped**
rather than imputed from the disclosure date.

## Point-in-time requirements

1. **Acceptance timestamp is the cutoff**, not filing date or period end.
2. **As-filed financial facts only.** A fact for fiscal period *P* is admissible
   only from a submission accepted at or before the observation's acceptance;
   where several qualify, the latest wins. APIs returning the *currently*
   reported value for a period are restatement-contaminated and excluded.
3. **Historical SIC**, read per accession from the DERA `sub` table. FIRE
   (6000–6799) is excluded on that value; unknown SIC is its own excluded state.
4. **CIK identity**, with no parent–child resolution. Registrant names are
   resolved point-in-time from EDGAR name history.
5. **Actual petition date** as event time.
6. **Exact `10-K` form match.** `10-K/A` and `10-KSB` are not observations, and
   an amendment is never substituted for a missing original.

## Cohort construction

A 10-K belongs to the cohort year of its acceptance timestamp. Rolling evaluation
tests cohort *Y* using only observations from cohort years strictly below *Y*, so
**2013–2024** are testable and 2012 is training-only. Per-cohort counts are in
`paper/tables/table1_cohort_statistics.md`.

**The 2021 cohort carries only 5 positives.** Its per-cohort metrics are
individually uninformative and should not be read as substantive findings.

## Feature arms

| arm | contents |
|---|---|
| **A — ratios** | 15 strict-PIT financial ratios from as-filed DERA facts, winsorised at fixed bounds, training-fold median imputation and standardisation |
| **B — text** | Item 1A (Risk Factors) and Item 7 (MD&A) from the observation's own 10-K; two separate TF-IDF vectorisers, 100,000 features each, word 1–2 grams, English stop words, sublinear TF, min_df 5, **fitted on the outer training period only**; missing section → zero block + binary indicator |
| **C — combined** | ratios ⊕ both text blocks ⊕ indicators, one logistic regression; no stacking, no ensembling, no embeddings, no transformers, no LLM features, no macro variables |

## Text coverage

| | ok | of 59,500 |
|---|---|---|
| Item 1A | 52,392 | 88.05% |
| Item 7 | 58,361 | 98.09% |
| both | 51,571 | 86.67% |
| at least one | 59,182 | 99.47% |

Positive-class coverage is higher: Item 1A 412/437, Item 7 435/437, both
410/437, **at least one section 437/437**.

## What is NOT redistributed, and why

**No SEC document payload is included in this release.** Specifically excluded:

- the 59,499 primary 10-K documents (141.83 GB raw / 10.16 GB stored);
- the extracted section cache (2.0 GB);
- the 8-K Item 1.03 document corpus;
- the SEC bulk submissions archive and the 52 DERA quarterly archives;
- all generated gate outputs and prediction files.

These are **public primary-source documents** available directly from the SEC.
Redistributing them would add tens of gigabytes to the release, risk serving a
stale mirror of records that can be amended, and duplicate a source that already
guarantees authenticity. The release instead ships the **tooling to reacquire
them** plus **SHA-256 hashes of every derived artifact**, so an independent
reproduction can be verified byte-for-byte against ours.

## How to reacquire the filings

See `REPRODUCIBILITY.md`. In short: acquire the bulk submissions archive and DERA
quarters, run the Gate 1 pipeline to rebuild the panel, then fetch the primary
10-K document of each frozen accession. Acquisition is rate-limited to 7.5
requests/second against the SEC's 8 rps benchmark cap, resumable, atomic, and
records a manifest with per-document SHA-256. A full retrieval is roughly two
hours of SEC traffic.

**Supply your own contact email** via `--email`; the SEC requires a real address
in the User-Agent. Do not run acquisition concurrently with other SEC ingestion.

## Known limitations

1. **Validation used blinded AI adjudication, not independent human ground
   truth.** The adjudicating model was also involved in classifier development,
   so reported agreement (93/95 confirmed, 0.9789, 95% CI [0.9265, 0.9942]) is
   **classifier-to-AI-adjudicator agreement** and is biased upward by correlated
   error in an unquantified way.
2. **Two known label errors remain**, identified during validation and
   deliberately uncorrected so the holdout was not converted to development data.
3. **Text extraction limitations.** 179 Item 1A sections (0.30% of the corpus,
   **zero positives**) carry recoverable risk-factor text under non-standard
   headings and are deliberately left missing. Filings that abandon item
   numbering entirely have no section terminator and are structurally undefined.
   5,788 Item 1A cases are smaller reporting companies stating the item is not
   required — correctly reported as missing rather than passed through.
4. **Survivor-universe caveat.** The survivorship analysis uses a *2024-filer*
   proxy. It is not survivorship in general, and its magnitude is mechanically
   strongest in early cohorts and zero in 2024.
5. **Label recall is not measurable from inside EDGAR.** Bankruptcies that
   Item 1.03 never reports require an external reference to detect.
6. **Statistical power.** At 437 positives the panel cannot resolve contamination
   effects at the ±10% relative scale.
7. **No contamination-inflates-everything claim.** The audit found that channels
   differ in direction, magnitude and estimand; one is negative, one is a
   composition change, one is untestable here. Do not cite this benchmark as
   evidence that contamination uniformly inflates performance.
8. **Scope.** US SEC registrants filing Form 10-K in English, 2012–2024, FIRE
   excluded. Results do not transfer automatically to private firms, other
   jurisdictions, or the excluded sectors.

## Licence and provenance

All source records are US SEC public filings. Derived artifacts in this
repository carry no third-party data. The benchmark's dependency footprint for
label construction is the Python standard library; the model arms additionally
use numpy, scipy and scikit-learn.
