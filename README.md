# EDGAR-X

**A point-in-time benchmark for predicting US Chapter 7 or Chapter 11 bankruptcy
within 365 days of a Form 10-K, using only information available at that
filing's EDGAR acceptance timestamp.**

Every input is fixed against one clock. A financial fact may enter an observation
only if it comes from a submission accepted at or before the observation's own
acceptance timestamp; industry classification is the SIC code carried on the
filing itself; registrant identity is the CIK printed on the document; the event
time is the actual bankruptcy petition date, not the date it was disclosed; and
training rows come only from cohorts strictly earlier than the cohort being
tested.

The working paper is [`paper/EDGAR-X_working_paper_v1.1.pdf`](paper/EDGAR-X_working_paper_v1.1.pdf).

## The benchmark

| | |
|---|---|
| Observational unit | one Form 10-K, identified by accession number, attributed to a CIK |
| Label | the same CIK filed an initial US Chapter 7 or Chapter 11 petition within 365 days of acceptance |
| Panel | **59,500** Form 10-K observations, 2012–2024 |
| Positive observations | **437** |
| Rolling-testable | **54,351** observations, **408** positive observations, cohorts 2013–2024 |
| Prevalence | 0.73% |
| Excluded | Finance, Insurance and Real Estate (SIC 6000–6799) on the as-filed code; unknown SIC |

**Positive observations are not necessarily distinct bankruptcy events.** One
bankruptcy can label more than one 10-K when two acceptances fall less than a
horizon apart, so counts of positive observations and counts of distinct events
are reported separately throughout. In the final panel, 437 positive
observations arise from 429 distinct CIKs.

## Headline results

Event-weighted average precision across the twelve test cohorts, from
[`benchmark/gate4_release/`](benchmark/gate4_release/):

| arm | event-weighted AP |
|---|---|
| Financial ratios | **0.0425** |
| Filing text (Item 1A + Item 7) | **0.1301** |
| Combined | **0.1447** |

Filing text over ratios: **+206.1% event-weighted relative AP**, positive in 12
of 12 cohorts.

**Scope of that conclusion.** All three arms use the same sparse linear model
family, L2-regularised logistic regression over TF-IDF and standardised ratios,
with an identical regularisation grid, selection rule, training cohorts and test
rows. The modality comparison is controlled within that family and is **not** a
claim about what a higher-capacity model would do, which was not tested.
**Combined features do not uniformly outperform text**: the combined-over-text
increment is +11.2% event-weighted, positive in 10 of 12 cohorts, with three
cohort intervals excluding zero positively and one negatively.

## Label validation

Classifier mapped-positive labels confirmed against a human reference standard:
**92 / 95 = 96.8%, Wilson 95% CI [0.9112, 0.9892]**.

What that figure is, precisely:

- It is **agreement with a human reading of the same filing text the classifier
  read**. No court record, docket or external database was consulted, so it is
  **not** an accuracy measurement against ground truth.
- Reviewer A supplied the judgements that became the final reference.
  **Reviewer B was an independent first-pass agreement check** across all 188
  cases. **Reviewer C reviewed the 29 substantive A/B disputes and selected
  Reviewer A's judgement for every disputed field**, without case-specific
  rationales. **This is not a conventional independently reasoned multi-reviewer
  consensus.**
- Reviewers did not develop the classifier and were blinded to classifier
  output, the earlier AI adjudication, the answer key and the sampling stratum.
- An earlier first pass used a blinded AI adjudicator that had been involved in
  developing the classifier. That pass is retained in the paper and in
  [`validation/`](validation/) as study history, not as evidence.

Methodology and aggregate results are in [`validation/`](validation/). Reviewer
packets, completed forms, the consensus file and the sealed answer key are **not
published**, to protect the reviewers and to keep the holdout usable.

## What this benchmark does not claim

- **No population accuracy, sensitivity, specificity, recall or prevalence
  estimate.** The validation holdout is stratified and supports none.
- **No label-recall claim.** Bankruptcies never disclosed under Item 1.03 are
  invisible to this construction. What is measured is label precision on
  discovered events.
- **No state-of-the-art claim**, and **no claim to be the first** point-in-time
  bankruptcy benchmark. The literature search behind the paper was not
  exhaustive.
- **No claim that contamination uniformly inflates measured performance.** Of
  four audited channels, one produced a negative point estimate, one changed the
  benchmark's composition rather than its scores, one lacked the positive-class
  exposure to be testable, and one was a heterogeneous protocol sensitivity. The
  audit is not causal.
- **No deployment claim.** Review-budget figures are ranking results; no
  threshold, operating point or cost model is proposed, and the probabilities
  are not calibrated.

## Repository layout

```
benchmark/        construction, point-in-time reconstruction, acquisition, tests
  gate4_release/  frozen authoritative metrics (per-cohort, aggregate, LOO, selected C)
protocols/        label policy, benchmark protocol, contamination audit, data card, limitations
validation/       human-validation protocol, amendments, analysis plan, aggregate results
paper/            working paper v1.1, figures, tables, bibliography
repro/            scripts that rebuild every table and figure from the frozen metrics
```

## Reproducing the tables and figures

Every public table and figure is a deterministic transformation of the frozen
CSVs in `benchmark/gate4_release/`. Nothing below fits a model.

```bash
pip install -r benchmark/requirements.txt
cd repro && python3 verify_reproduction.py
```

That rebuilds all 18 table artifacts and all ten figure files and compares them
against the shipped copies, reporting any mismatch rather than correcting it.
Figure PDFs embed a creation timestamp, so they are compared with `/CreationDate`
stripped; everything else is compared byte for byte.

See [`protocols/REPRODUCIBILITY.md`](protocols/REPRODUCIBILITY.md) for the full
pipeline and for which stages are expensive.

## Source data

**No SEC document is redistributed here.** The corpus is reacquirable from SEC
primary sources with the tooling in `benchmark/`.

The SEC caps clients at 10 requests per second and requires a `User-Agent`
header carrying a real contact email. `benchmark/sec_download.py` enforces a
rate limit below that cap and **takes the contact address from the command
line**; it will refuse a placeholder. Acquiring the full 10-K corpus takes many
hours and is not something to start casually.

## Status

Working paper, not peer reviewed. No DOI, no venue, no publication status is
claimed.

## Licence

Code is MIT; documentation, the paper and the generated figures and tables are
CC BY 4.0. See [`LICENSE`](LICENSE), [`LICENSE-DOCS`](LICENSE-DOCS) and
[`NOTICE.md`](NOTICE.md), which records what is and is not covered.

## Citation

See [`CITATION.cff`](CITATION.cff).

## Contact

**Bhavya Upadhyay**
officiallybhavya@gmail.com
