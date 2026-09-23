# EDGAR-X — Limitations

Read this before citing any number from EDGAR-X. Frozen at
`dcee1037bcb21e358be531d988e147fd7641e696`.

---

## 1. Validation is not ground truth

**The label validation used blinded AI adjudication, not independent human
adjudication.** The protocol pre-registered a human reviewer; that is not what
happened, and the deviation is recorded in `FINAL_VALIDATION_PROTOCOL.md`
Amendment 2.

The blinding held operationally — the adjudicator saw only the filing text and
never the automated disposition, petition date, stratum or answer key, which was
opened only after all 188 labels were frozen, hashed and committed. **But the
adjudicating model had also been involved in developing the classifier it
reviewed.** Shared priors about how Item 1.03 language maps to debtor identity,
chapter and petition date are exactly what the classifier encodes.

Reported agreement — **93/95 mapped positives confirmed, 0.9789, Wilson 95% CI
[0.9265, 0.9942]** — is therefore **classifier-to-AI-adjudicator agreement**, not
accuracy against ground truth. Correlated error biases it **upward by an
unquantified amount**.

**Superseded in Phase 2A.** Independent human adjudication of the same frozen
holdout has since been carried out. Against that human reference, **92 of 95**
mapped positives are confirmed: 0.9684, Wilson 95% CI [0.9112, 0.9892]. That
figure is agreement with a human reading of the same filing text, not accuracy
against a court record, and the reference equals one reviewer's judgements
ratified by a second. See `../validation/RESULTS.md` and `../validation/PROVENANCE.md`.

## 2. Two known label errors remain

Validation identified two genuine false positives, both deliberately left
uncorrected so the holdout was not converted into development data:

- a registrant that is a **CCAA** debtor in Canada while its US and Irish
  subsidiaries filed the Chapter 11 petitions;
- a Chapter 7 debtor that is a **subsidiary sharing the registrant's exact name**
  in a different state of incorporation.

Both remain positive in the benchmark.

## 3. Do not claim contamination uniformly inflates performance

This is the limitation most likely to be mis-cited. **The audit found that four
contamination channels differ substantially in direction, magnitude, and even
estimand:**

- **restatement** produced a **negative** effect (−10.49% relative), not an
  inflation;
- **survivor universe** is a **composition** change (−77.7% of positives), not a
  scoring effect, and no powered AP effect is claimed for it;
- **SIC vintage** touched 4,248 observations but only **two positives**, so it was
  never modelled;
- **random versus rolling splitting** produced heterogeneous protocol sensitivity
  whose standard remedy — grouping folds by firm — **does not remove it**.

EDGAR-X must not be cited as evidence that contamination uniformly inflates
measured performance.

## 4. Statistical power

The panel carries **437 positives at 0.73% prevalence**. A paired design at 341
positives has a **minimum detectable effect of roughly 24–33% relative**. Null
findings in the contamination audit therefore bound **dominance, not existence**,
and any study reporting precise contamination effects on a comparable panel
should state its own minimum detectable effect.

## 5. Sparse cohorts

**The 2021 cohort has only 5 positives.** Its average precision is high and
unstable, and it must not be read as a substantive finding. Event weighting gives
it 1.2% of the aggregate; cohort mean and median views are more exposed to it,
which is why all four aggregation views are reported together.

## 6. Survivor-universe caveat

The survivorship channel uses a **2024-filer proxy**: a registrant counts as
surviving if it filed anything with EDGAR in 2024. This is conservative — a
delisted firm that still files counts as surviving — so it **understates**
exposure, and it is **not survivorship in general**. Delisting, index membership,
ticker-map coverage, vendor back-fill and acquisition behave differently.

The filtering is also **mechanically strongest in early cohorts and exactly zero
in 2024**, since a registrant that filed a 10-K in 2024 necessarily satisfies the
condition. Part of the measured magnitude is elapsed time, not firm mortality.

## 7. Text-extraction limitations

- **179 Item 1A sections** (0.30% of the corpus, **zero positives**) carry
  recoverable risk-factor text under combined or non-standard headings
  (`ITEMS 1., 1A., and 2.`, or a bare `RISK FACTORS`) and are **deliberately left
  missing** under the frozen policy.
- **21 filings abandon item numbering entirely**, leaving no terminator; section
  extraction is structurally undefined for them.
- **5,788 Item 1A cases** are smaller reporting companies stating the item is not
  required. These are correctly reported as missing rather than passed through as
  substantive text.
- Item 1A coverage is **88.05%** and Item 7 **98.09%**; no observation is dropped
  for missing text, which instead contributes a zero block plus an explicit
  indicator.

## 8. Calibration is not claimed

**No arm is calibrated, and none is described as such.** `class_weight="balanced"`
changes the raw probability scale, most severely for the ratio arm, whose Brier
scores near 0.2 reflect inflated probabilities rather than poor ranking.

**AP, ROC-AUC and review-budget metrics are the primary predictive comparisons.**
Brier score, calibration intercept and calibration slope are diagnostics of raw
frozen logistic outputs only. No post-hoc recalibration was performed, and any
such experiment would need separate pre-registration.

## 9. Review-budget results are not deployment claims

Precision, recall and lift at fixed budgets describe **ranking quality under a
fixed analyst review capacity**. No threshold, operating point, cost model or
decision rule is proposed, and nothing here supports a deployment claim.

## 10. Label recall is not measurable from inside EDGAR

Bankruptcies that Item 1.03 never reports cannot be detected from SEC filings
alone. Measuring label **recall** requires an external reference such as a public
court database. What this benchmark measures is label **precision** on the events
it does find.

## 11. Regularisation

The temporal selection procedure **frequently preferred the weakest
regularisation available in the frozen grid** — text and combined arms selected
`C = 10` in eight of the final ten cohorts. This is an observation about the
procedure on this grid, **not** a claim that `C = 10` is globally optimal. The
grid was not expanded after results were seen.

## 12. Model family by design

Sparse linear models over TF-IDF were chosen for reproducibility and to keep the
point-in-time contract auditable. **Stronger text models may well change effect
sizes.** They would not change the protocol, and evaluating them is future work.

## 13. Scope

US SEC registrants filing Form 10-K in English, **2012–2024**, with Finance,
Insurance and Real Estate (SIC 6000–6799) excluded, and unknown-SIC observations
excluded as their own state. Results do not transfer automatically to private
firms, non-US jurisdictions, or the excluded sectors.

## 14. Single-panel evidence

Every finding rests on **one panel, one label definition and one horizon**. The
contamination channels were each measured once. Replication on an independent
panel — a different jurisdiction, horizon or outcome definition — has not been
attempted.
