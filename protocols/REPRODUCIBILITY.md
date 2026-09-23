# EDGAR-X — Reproducibility

**Frozen at** `dcee1037bcb21e358be531d988e147fd7641e696`.
Every number in the manuscript traces to a tracked artifact under
`gate4_release/` or to a frozen result document in this directory.

---

## What ships, and what does not

**Tracked (small, ~72 KB):** the pre-registered protocols, the frozen result
documents, and `gate4_release/` — per-cohort metrics, aggregates, selected
regularisation, leave-one-cohort-out influence, and a manifest hashing every
untracked artifact.

**Not tracked, by design:** SEC document payloads, the extracted section cache,
the bulk submissions archive, DERA quarterly archives, and all generated gate
outputs and prediction files. These are reacquirable from primary sources and
verifiable against the recorded hashes. See `DATA_CARD.md` for the rationale.

`gate4_release/artifact_manifest.csv` lists **44 untracked artifacts totalling
103.5 MB** with path, byte count and SHA-256.

---

## Environment

- Python 3.12
- Label construction (Gate 1): **standard library only**
- Model arms: `numpy`, `scipy`, `scikit-learn` — see `requirements.txt`
- Disk: ~15 GB for the document corpus and section cache
- Wall clock: ~2 h acquisition, ~30 min cache build, ~12 h full benchmark

The benchmark is a **flat directory with no `__init__.py`**; modules import each
other unqualified so the directory survives being zipped or copied file by file.
`package_test.py` verifies this by zipping an explicit MANIFEST, extracting it to
an empty directory and running the suites from there.

---

## Reproduction, end to end

### 1. Acquire primary sources

```bash
cd research/bankruptcy_benchmark
python3 prepare_gate1_data.py --email you@your-domain.example
```

Fetches the SEC bulk submissions archive, 52 DERA quarters (2012q1–2024q4), and
the primary 8-K document of every Item 1.03 candidate. Resumable; refuses to
report success on materially incomplete inputs.

**Supply a real contact address.** The SEC requires one in the User-Agent and the
acquisition test asserts that a placeholder is rejected. Do not run concurrently
with other SEC ingestion — the clients do not share a rate limiter.

### 2. Rebuild the panel and labels

```bash
python3 event_counts.py
```

Produces the disposition census, the event–observation map and the cohort vector.
Expected: 3,786 Item 1.03 filings → 3,010 events → 59,500 eligible observations
with 437 positives.

### 3. Build the ratio panel

```bash
python3 gate2_extract.py    # DERA sub/num extraction
python3 gate2_panel.py      # strict-PIT ratio panel
```

### 4. Acquire the 10-K text corpus

```bash
python3 gate3_tenk_inventory.py
python3 gate3_acquire_tenk.py --email you@your-domain.example --workers 8
python3 gate3_reconcile.py --verify-hashes
```

Rate-limited to **7.5 requests/second** under a single shared limiter (the
benchmark cap is 8 rps), resumable through its manifest, atomic writes, bounded
retries, **no `10-K/A` substitution**. `gate3_reconcile.py` asserts the terminal-state
partition, verifies every file against its manifest SHA-256, and reports
byte-identical duplicate content as a read-only diagnostic.

Expected: 59,499 retrieved, 0 failures, 0 mismatches, 141.83 GB raw / 10.16 GB
stored.

### 5. Extract sections and audit

```bash
python3 gate3_text_audit.py --documents 10k_text
python3 gate3_extraction_qa.py
```

Expected: Item 1A 52,392 ok, Item 7 58,361 ok, both 51,571.

### 6. Cache sections for the benchmark

```bash
python3 gate4_build_text_cache.py --workers 8
```

**This step verifies itself.** Every cached outcome and section length is compared
against the frozen audit, and the run aborts on any mismatch. Expected:
`EQUIVALENCE PASSED`, 0 mismatches across all 59,500 observations.

### 7. Run the benchmark

```bash
python3 gate4_benchmark.py      # 36 units, resumable, ~12 h
python3 gate4_summarize.py
```

Resumable at `(population, cohort)` granularity: a unit's predictions file is
written atomically and only after the unit completes, so an interrupted unit is
recomputed from scratch and never treated as complete.

### 8. Rebuild manuscript figures and tables

```bash
cd ../../paper/figures && for f in fig*.py; do python3 "$f"; done
cd ../tables && python3 build_tables.py
```

These read **only** `gate4_release/*.csv` and recompute nothing.

---

## Determinism

| component | seed / rule |
|---|---|
| validation sampling | 20260916 |
| validation review order | 20260917 |
| contamination matched-volume draws | 20260921 + 1000·(year−2013) + draw |
| benchmark random-split diagnostic | 20260920 |
| paired CIK-cluster bootstrap | 20260916, 2,000 replicates |
| QA packet | 20260920 |
| regularisation grid | `C ∈ {0.01, 0.1, 1.0, 10.0}`, fixed |

Model selection is deterministic given the data: the inner validation window is
the most recent contiguous prior cohorts holding ≥25 positives, candidates train
only on cohorts preceding that window, and 2013–2014 take the pre-registered
`C = 1.0` fallback. **No test cohort or future cohort enters selection.**

---

## Verifying an independent reproduction

1. Compare your `outputs/gate3/tenk_acquisition_manifest.csv` per-document
   SHA-256 values against ours. Filings can be amended, so a small number of
   mismatches indicates SEC-side revision rather than a reproduction error;
   investigate rather than assuming either outcome.
2. Confirm `gate4_build_text_cache.py` reports `EQUIVALENCE PASSED`.
3. Compare `gate4_release/cohort_metrics.csv` directly. Logistic regression with
   `lbfgs` is deterministic, so per-cohort AP should match to solver tolerance.
4. Hash-check derived artifacts against `gate4_release/artifact_manifest.csv`.

---

## Guardrails enforced in CI

```bash
./research/check_import_boundary.sh     # benchmark imports nothing from the production pipeline
cd research/bankruptcy_benchmark
python3 package_test.py                 # MANIFEST zips, extracts and runs clean
python3 integration_test.py             # 152 checks
python3 gate3_extraction_test.py        # 24 adversarial extraction checks
python3 gate3_acquire_test.py           # 10 acquisition/denominator checks
```

The import boundary is not stylistic. The production pipeline resolves identity
through a present-day ticker map, discards acceptance timestamps, and prefers
restated facts over as-filed ones — every convention this study measures the cost
of. Importing it would answer the research question in advance, with the wrong
answer.
