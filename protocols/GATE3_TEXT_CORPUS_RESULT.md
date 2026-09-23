# Gate 3 Text Corpus Result — retrieval and extraction

**Date:** 2026-09-20
**Status:** FROZEN. The extractor is frozen; no further extraction changes.
**Code:** `gate3_tenk_inventory.py`, `gate3_acquire_tenk.py`, `gate3_reconcile.py`,
`gate3_item_extraction.py`, `gate3_text_audit.py`, `gate3_extraction_qa.py`

---

## 1. Retrieval

| quantity | value |
|---|---|
| benchmark observations | **59,500** |
| retrieved primary documents | **59,499** |
| no-primary-document observations | **1** (a 2021 negative, `0001108524-21-000014`, CIK 1108524) |
| **positive-class documents retrieved** | **437 / 437** |
| HTTP / retrieval failures | **0** (permanent 0, retryable 0, malformed 0) |
| retry attempts | **0** |
| HTTP status distribution | 200 → 52,216; nothing else |
| SHA-256 mismatches | **0** |
| missing local files among successful rows | **0** |
| raw bytes / stored bytes | 141.83 GB / 10.16 GB (13.96× compression) |
| configured / measured request rate | 7.5 rps (cap 8) / **7.095 rps** over 2.04 h, 8 workers |

**Two denominators, permanently separated.** The benchmark observation
denominator is **59,500** and is used only for coverage partitions. The retrieval
target denominator is **59,499** and is used for every HTTP progress, rate and
success figure. The single no-primary observation belongs to the first and never
the second: zero HTTP requests were issued for it.

**Terminal-state partition** (all assertions passed): mapped-and-retrieved
59,499 / 437 positives; mapped-to-shared-target 0; retrieval-failed 0;
no-primary-document 1; not-yet-attempted 0. Benchmark states sum to 59,500 and
retrieval states to 59,499. Zero duplicate `(CIK, accession, document)` targets.

## 2. Extraction coverage

| | ok | of 59,500 |
|---|---|---|
| **Item 1A** | **52,392** | **88.05%** |
| **Item 7** | **58,361** | **98.09%** |
| **both sections** | **51,571** | **86.67%** |
| **at least one section** | **59,182** | **99.47%** |
| neither section | 318 | 0.53% |

## 3. Positive-class coverage

| | ok | of 437 |
|---|---|---|
| **Item 1A** | **412** | **94.28%** |
| **Item 7** | **435** | **99.54%** |
| **both sections** | **410** | **93.82%** |
| **at least one section** | **437** | **100.00%** |

Positive coverage exceeds corpus-wide coverage on every measure, and **no
positive lacks both sections**. Positives missing Item 1A: 21 `too_short`,
3 `no_heading`, 1 `no_terminator`. Positives missing Item 7: 2 `too_short`.

## 4. Failure taxonomy

| outcome | Item 1A | Item 7 |
|---|---|---|
| ok | 52,392 | 58,361 |
| no_heading | 1,303 | 108 |
| no_terminator | 16 | 12 |
| too_short | 5,788 | 1,018 |
| empty_document | 0 | 0 |
| document_unavailable | 1 | 1 |

The 5,788 Item 1A `too_short` cases are **correct behaviour**, not failures:
smaller reporting companies stating the item is not required. The extractor
reports them rather than passing a one-sentence stub through as substantive text.

## 5. Section-length distributions (characters)

| section | min | p10 | median | p90 | max |
|---|---|---|---|---|---|
| Item 1A | 1,011 | 21,137 | **57,499** | 147,393 | 700,033 |
| Item 7 | 1,035 | 13,655 | **49,095** | 98,234 | 969,941 |

## 6. Frozen extractor limitation — 179 recoverable-but-unrecovered Item 1A cases

All 1,303 Item 1A `no_heading` observations were examined, not just the QA
sample. The QA sample of 12 was unrepresentative: 5 of 12 mentioned "risk
factors" against 13.7% in the population, which is why the full scan was run.

| category | count | positives |
|---|---|---|
| A — combined `ITEMS 1., 1A., and 2.` heading | 27 | 0 |
| B — plural `ITEMS` heading with substantive risk text | 38 | 0 |
| C — no item numbering at all, bare `RISK FACTORS` heading | 21 | 0 |
| D — item headings exist, risk text under a bare heading | 114 | 0 |
| **E — genuinely no substantive risk text** | **1,103 (84.6%)** | 3 |

**179 observations (categories A, B, D) = 0.30% of the corpus, 0 positives, are
recoverable in principle and are deliberately NOT recovered.** They remain
missing under the frozen missing-text policy: a zero text block plus the
`item_1a_missing` indicator. Category C (21) is structurally undefined — with no
item numbering there is no terminator to bound the section.

No sampled `no_heading` case contains an "Item 1A" token anywhere in its text, so
the anchor is not missing ordinary headings. The misses are the plural/combined
heading form and filings that abandon item numbering entirely.

**This is recorded as a frozen extractor limitation. The extractor is not
changed, and these observations are not modified.**

## 7. QA packet

`outputs/gate3/extraction_qa_packet.md` (365 KB) and `.csv`. Seed **20260920**,
**180 cases**, 12 per stratum per section, each carrying the extracted section
truncated to 1,800 characters plus 600 characters of neighbouring filing text on
each side so boundaries can be verified by eye.

**Strata: 10 defined, 9 populated.** The earlier report said "10 strata" without
qualification, which was wrong. The correct statement:

| stratum | cases |
|---|---|
| random_ok | 24 |
| positive | 24 |
| shortest_ok | 12 |
| longest_ok | 12 |
| duplicate_headings | 24 |
| no_heading | 24 |
| no_terminator | 24 |
| too_short | 24 |
| malformed | 12 |
| **`empty_document`** | **0 — defined but empty** |

The tenth stratum is **`empty_document`**. It drew zero cases because the corpus
contains zero `empty_document` outcomes for either section, as the taxonomy in §4
shows. Documentation only; the QA sample was not regenerated.

## 8. Byte-identical duplicate content

Read-only integrity diagnostic: 59,495 distinct content hashes among 59,499
retrieved documents. **4 hashes appear twice, 8 documents, 0.01% of the corpus,
6 distinct CIKs, 0 positives.**

| sha256 (first 16) | accession | CIK | cohort | label | bytes |
|---|---|---|---|---|---|
| `1c824def344d6d4c` | 0001342936-12-000012 | 1342936 | 2012 | 0 | 847,263 |
| `1c824def344d6d4c` | 0001342936-12-000013 | 1342936 | 2012 | 0 | 847,263 |
| `9abea83423fca54f` | 0001193125-12-117548 | 1038363 | 2012 | 0 | 1,901,901 |
| `9abea83423fca54f` | 0001193125-12-156471 | 1357787 | 2012 | 0 | 1,901,901 |
| `a1ce1edde44fc95c` | 0001144204-16-091540 | 714284 | 2016 | 0 | 837,927 |
| `a1ce1edde44fc95c` | 0001144204-16-091541 | 714284 | 2016 | 0 | 837,927 |
| `ddf7c772d0f72111` | 0001649338-16-000151 | 1649338 | 2016 | 0 | 4,287,997 |
| `ddf7c772d0f72111` | 0001649345-16-000016 | 1649345 | 2016 | 0 | 4,287,997 |

Two pairs are same-CIK consecutive accessions; **two pairs are cross-CIK**
(1038363/1357787 and 1649338/1649345), meaning a byte-identical filing yields
identical text features under two different registrants. Duplicate content is not
assumed to be an error — a filer can legitimately submit the same primary
document under two accessions.

### Frozen handling, fixed before any benchmark performance was observed

1. **All observations are preserved in the primary benchmark.** None of these 8 is
   removed from Option B.
2. **Mandatory duplicate-content exclusion sensitivity.** Final benchmark metrics
   are recomputed with all 8 observations participating in byte-identical
   cross-target duplicate pairs excluded. This is a sensitivity analysis only.

Recorded in `outputs/gate3/duplicate_content_pairs.json`.

## 9. Artifacts

`outputs/gate3/`: `tenk_document_inventory.csv`,
`tenk_acquisition_manifest.csv`, `retrieval_accounting.csv`,
`text_coverage_audit.csv`, `text_extraction_outcomes.csv`,
`extraction_qa_packet.{csv,md}`, `duplicate_content_pairs.json`. All generated
and untracked; no SEC payload enters git.
