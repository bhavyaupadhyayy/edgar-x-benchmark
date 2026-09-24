# EDGAR-X: a point-in-time bankruptcy-prediction benchmark

**Status: the empirical study is complete and frozen** at
`dcee1037bcb21e358be531d988e147fd7641e696`. No further experiments will be run.

A point-in-time benchmark for predicting **US Chapter 7 or Chapter 11 bankruptcy
within 365 days of a Form 10-K filing**, where every input is reconstructed as it
existed at prediction time: as-filed financial facts, historical SIC, CIK
identity, EDGAR acceptance timestamps, and the actual petition date as event
time.

| | |
|---|---|
| observations (2012–2024) | **59,500** |
| positives | **437** (prevalence 0.73%) |
| rolling-testable (2013–2024) | **54,351** observations / **408** positives |
| 10-K documents retrieved | 59,499 · zero failures · zero checksum mismatches |

**Headline result.** Filing text substantially outperforms financial ratios under
strict temporal evaluation: event-weighted average precision **0.0425 → 0.1301**
(**+206%**, positive in **12 of 12** cohorts). Ratios + text reaches **0.1447**
(+240% over ratios), but ratios add only a modest, heterogeneous increment over
text alone (+11.2%, 10/12 cohorts, three intervals excluding zero, one cohort
significantly negative).

**Contamination audit.** Four information-set contamination channels were
audited with signed effects and pre-registered decision rules. **Their effects
differ substantially in direction, magnitude, and even estimand.** Do not cite
this work as evidence that contamination uniformly inflates performance.

### Read these first

| document | contents |
|---|---|
| [`DATA_CARD.md`](DATA_CARD.md) | what the benchmark contains, exact label definition, PIT rules, feature arms |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | end-to-end reproduction, seeds, verification |
| [`LIMITATIONS.md`](LIMITATIONS.md) | all standing limitations — **including that validation used blinded AI adjudication, not human ground truth** |
| [`FINAL_EMPIRICAL_FINDINGS.md`](FINAL_EMPIRICAL_FINDINGS.md) | the complete empirical story |
| [`GATE4_FINAL_BENCHMARK_RESULT.md`](GATE4_FINAL_BENCHMARK_RESULT.md) | frozen benchmark results |
| [`CONTAMINATION_FINDINGS_FREEZE.md`](CONTAMINATION_FINDINGS_FREEZE.md) | all four contamination channels, closed |

Tracked results live in [`gate4_release/`](gate4_release/) (72 KB). **No SEC
document payload or text cache is redistributed** — see `DATA_CARD.md` for why,
and `REPRODUCIBILITY.md` for how to reacquire it.

---

## Module layout

Flat layout on purpose: modules import each other as siblings, so the directory
survives being zipped, flattened, or copied one file at a time. The listing below
covers the original feasibility gates; the later pipeline stages are
`gate2_*` (ratio panel and contamination), `gate3_*` (text corpus and
extraction) and `gate4_*` (the benchmark).

```
constants.py             study design + statistical conventions
panel_simulation.py      panel model, average precision, both estimands
power_analysis.py        GATE 2 driver, correlation sensitivity (no network)
submissions_scan.py      GATE 1 discovery from the bulk archive (no network)
event_classification.py  GATE 1 rules: registrant Ch 7/11 vs receivership vs subsidiary
filing_history.py        GATE 1 history: complete filings, acceptance timestamps
event_counts.py          GATE 1 driver: bounded per-cohort event vector
```

## The observational unit

A registrant identified by CIK filing a Form 10-K. The positive outcome is that
same legal registrant entering Chapter 7 or Chapter 11 within 365 days of the
filing's acceptance. No parent-child resolution is attempted anywhere. A
subsidiary filing the registrant is not party to is not this registrant's
event.

## Three quantities that must stay separate

- **Label recall**: bankruptcies Item 1.03 never reports. Not measurable from
  inside EDGAR. Needs an external reference; the Federal Judicial Center's
  public bankruptcy database is free, public domain, and preserves the study's
  license-free claim.
- **Eligibility loss**: known events with no same-CIK predecessor 10-K. Counted
  by `event_counts.py`.
- **Outcome censoring**: eligible 10-K observations whose 365-day outcome
  cannot be confidently observed, e.g. a Form 15 mid-horizon. This is where the
  three-state label belongs, and it is the only one of the three that is
  censoring.

## Gate 1

```
python3 event_counts.py --submissions ./submissions.zip --documents ./8k_text/ \
    --start 2012 --end 2024
```

Needs the SEC bulk submissions archive and a local cache of primary 8-K
documents for the Item 1.03 candidates. Discovery itself needs no network.

Output is a **bounded** count: a lower bound of rules-confirmed registrant
Chapter 7/11 events and an upper bound adding the ambiguous cases. Run Gate 2
at both.

## Gate 2

```
python3 power_analysis.py
```

Reports both estimands across score correlations 0.50 / 0.70 / 0.90 / 0.95.

```
GO           useful at correlation 0.70
CONDITIONAL  only useful at 0.90 or above
KILL         not useful even at 0.95
```

## Estimands

```
absolute  D = sum_k w_k (AP_con_k - AP_pit_k)
relative  R = sum_k w_k (AP_con_k - AP_pit_k) / sum_k w_k AP_pit_k
```

Event weights, `w_k` proportional to fold event count. R is a ratio of
event-weighted sums, not an average of per-fold ratios: the per-fold form lets
one quiet year with an accidentally low PIT AP dominate the statistic. Both are
simulated directly, so each carries its own standard error.

## What is and is not in the package

`package_test.py` manifests 17 source files. Anything else in the directory is
generated output, not part of the distributable: `power_grid.csv`,
`event_counts.csv`, `disposition_census.csv`, `event_observation_map.json` and
`edgar-x-bench.zip`. A listing with more entries than the manifest is expected
and is not a packaging fault; MANIFEST, not the directory, defines the package.
If a source module is ever added, add it to MANIFEST in the same commit or the
package test will fail, which is the intended behaviour.

## Data acquisition

```
python3 prepare_gate1_data.py --email you@domain.com
```

Downloads only what Gate 1 needs: the bulk submissions archive, the 52 DERA
quarters covering 2012-2024, and the primary 8-K document of each Item 1.03
candidate. Candidates come from archive metadata, so the document cache is
candidate-sized and the full EDGAR corpus is never touched.

Resumable: cached files are skipped, downloads are atomic via .part rename, and
the run refuses to report success when inputs are materially incomplete.

Endpoints, verified against SEC documentation in September 2026:

```
https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip
https://www.sec.gov/files/dera/data/financial-statement-data-sets/{YYYY}q{Q}.zip
https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primaryDocument}
```

## Before running Gate 1, run the tests

```
python3 package_test.py      # zips, extracts to an empty dir, runs both suites there
python3 integration_test.py  # end-to-end wiring check in place
python3 acquisition_test.py  # download failure modes, offline
```

`package_test.py` exists because v5 passed every integration assertion locally
and shipped a package missing two modules. Integration tests prove the code
works where it was written. The package test proves it works where it lands.

## Integration test

```
python3 integration_test.py
```

Builds a tiny synthetic archive and asserts that every component is actually
invoked by the Gate 1 driver. Three fixes in v4 existed as modules that nothing
called; this test is what makes that failure mode loud instead of silent. Run
it before Gate 1, every time.

## What changed from v6

- `sec_download.py` and `prepare_gate1_data.py`: the acquisition layer, which
  did not exist before. Rate limiting, User-Agent enforcement, content
  validation, atomic caching, resume, and loud blockers.
- `acquisition_test.py`: 20 offline checks on the download failure modes.
- `submissions_scan.py` carries `primaryDocument`, so a candidate's document
  URL is constructible without an index lookup. Gate 1 could not fetch
  documents without this.
- `package_test.py` runs both suites from the extracted directory.

## What changed from v5

- `package_test.py`: explicit file manifest, zip, extract into an empty
  directory, assert the manifest survived, run the suite from there.
- The amendment flag is carried into `assemble_events` and the 120-day
  proximity rule is restricted to actual /A filings. An ordinary 8-K is never
  absorbed by proximity, which would merge two genuine bankruptcies.
- An /A can now complete an event that has neither petition date nor docket.
  That is the case amendment merging exists for, and v5 did not handle it: the
  original had no identity to match on. The fixture now tests exactly this.
- Multiplicity is reported separately for confirmed positives and the
  upper-bound sample.
- The three negative merge guards are checked in, not run ad hoc. They pin the
  amendment window to /A filings; without them a later loosening of the merge
  rule would still pass every positive assertion.

## What changed from v4

- `event_counts.py` now orchestrates the full chain. The SIC index is built and
  attached, amendments are merged into event records, petition date is the
  event time, and `label_observations` replaces the latest-only predecessor
  lookup.
- Event time is the parsed petition date. An unparsed date goes to
  `event_date_unresolved`; the disclosure timestamp is never substituted.
- Court and docket are extracted, so the strong event key can be built.
- Missing SIC is a third state, excluded from the primary benchmark and
  counted, instead of defaulting to eligible.
- Gate 1 writes `event_observation_map.json`, the real dependence structure for
  final Gate 2, including events whose 10-Ks span two cohort years.

## What changed from v3

- `sic_as_filed` is now actually populated, via `dera_sic.py`. Until this join
  existed the FIRE exclusion excluded zero firms, because the field was always
  None and the exclusion treats None as not-FIRE.
- 8-K/A amendments are tagged and collapsed by event identity instead of being
  counted as separate bankruptcies. Accession-level deduplication does not do
  this; an amendment has its own accession.
- `observation_labels.py` returns every 10-K a bankruptcy labels, not the
  latest, and Gate 1 reports unique events and positive observations
  separately.
- Classification reads only the Item 1.03 section.
- Gate 2 accepts a duplicate-positive rate, so multiplicity deflates effective
  event count rather than being assumed away.

## What changed from v2

- Correlation sensitivity grid, replacing a single assumed value.
- Relative inflation is simulated as a ratio statistic with its own standard
  error, instead of the absolute MDE rescaled by a constant.
- EDGAR full-text search is gone. The bulk archive already carries 8-K item
  codes, which removes the pagination cap, the exhibit duplicates, the
  undocumented endpoint, and every network call after one download.
- Item 1.03 candidates are classified before being counted. Receivership and
  subsidiary-only events are not the study's label.
- FIRE exclusion uses SIC as filed, not the present-day company profile.
  Renamed from "financial" because 6000-6799 is the whole FIRE block.
- Eligibility loss is no longer called informative censoring.

## Assumptions still unvalidated

- Classification rules are unaudited. Hand-label at least 100 random candidates
  before the bounded count gates anything, and report rule precision and recall
  per disposition.
- The `items` field is assumed complete. A systematically blank field would
  look exactly like an absence of bankruptcies.
- Petition date is extracted as raw text, not parsed or reconciled against
  court records.
- Power figures use a normal approximation applied to a Monte Carlo standard
  error. Adequate for a design gate, not for the manuscript. Validate a few
  cells with direct rejection rates under simulated null and alternative.
- Shell-company exclusion is unimplemented; the cover-page XBRL flag is the
  right source and needs parsed filings.
