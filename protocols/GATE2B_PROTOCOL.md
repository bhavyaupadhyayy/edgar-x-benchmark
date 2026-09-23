# Gate 2B Protocol — information-set violations other than restatement

**Date:** 2026-09-16
**Status:** pre-registered. Written before any Gate 2B exposure figure was
computed and before any Gate 2B model was fitted.

## Revised scientific question

> How do distinct violations of the historical information set change measured
> bankruptcy-prediction performance, and which channels materially matter?

**Effects are signed.** Gate 2A found a negative effect where the design
anticipated a positive one. No channel here is assumed to improve AP, and no
result will be reported as a failure for having the "wrong" sign.

## Scope

Only contamination channels already contemplated in the EDGAR-X design
(`docs/PIT_CONTRACT.md` §2) are in scope:

1. **Survivor / universe construction**
2. **Non-point-in-time entity identity / present-day mappings**
3. **Improper temporal evaluation / random splitting**

No new leakage channels are invented. The restatement / later-facts channel is
closed by `GATE2A_RESULT.md` and is not revisited, re-specified or re-run.

## Inherited constraints

Frozen and not touched by anything in this protocol: Gate 1 labels, the frozen
AI validation, the restatement contamination definition, the 365-day outcome
horizon, the bankruptcy label definition, the feature set (financial ratios
only — no text, LLM, macro or multimodal features), the model family
(`LogisticRegression`, `C=1.0`, `class_weight="balanced"`, no search), and the
bootstrap settings (2,000 replicates, CIK clusters, seed 20260916).

Every Gate 2B panel inherits the **strict validation-CIK exclusion**: all 188
CIKs in the frozen final-validation sample are removed before any split.
Baseline strict panel: **58,789 observations, 341 positives, prevalence
0.0058**, cohorts 2012–2024.

---

## Channel 1 — survivor / universe construction

| | |
|---|---|
| **Strict-PIT arm** | Every 10-K observation eligible as of its own acceptance date: as-filed SIC known and outside FIRE (6000–6799). Inclusion does not depend on anything after the acceptance timestamp. |
| **Contaminated arm** | The same observations, restricted to registrants reachable through the **present-day filer universe**. Documented mechanism: `EdgarClient._resolve_ticker` resolves identity through today's `company_tickers.json`, so a registrant absent from today's map is simply never retrieved. |
| **Operational definition of "present today"** | The CIK has at least one EDGAR submission in the DERA index dated in the final year of the window (2024). This is a **proxy** and is stated as one: it captures "still an active filer", not "still listed under a ticker". It is conservative — a delisted firm that still files is counted as surviving — so it **understates** survivorship exposure. |
| **Unit of analysis** | One 10-K observation (accession), identified by CIK. |
| **Observation membership changes?** | **Yes**, by construction. That is the channel. |
| **Pairing possible?** | Only on the common intersection (estimand A). Not for the composition estimand (estimand B). |

This channel is split into two estimands, deliberately, because they answer
different questions and only one of them can be paired.

### Estimand A — common-intersection effect

Restricted to observations present in **both** universes, i.e. the surviving
registrants' observations.

> For the same historical observations, does survivor-biased universe
> construction change model scores and measured performance?

Rows genuinely match — same accession, same label, same features — so **paired
inference is valid**: paired CIK-cluster bootstrap over identical test rows,
exactly as in Gate 2A. The only difference between arms is the training
universe the model was fitted on.

- **Primary metric:** signed ΔAP on the intersection test set.
- **Secondary:** ROC-AUC, score correlation between arms, rank shift on
  positives versus negatives.

### Estimand B — benchmark-composition effect

Full PIT universe versus the survivor-contaminated universe.

> How much does changing *who is in the benchmark* alter reported performance
> and prevalence?

Membership differs, so **paired inference is not used and will not be forced**.
Each arm is evaluated on its own test set and compared by unpaired
CIK-cluster bootstrap of the difference in AP, with prevalence reported
alongside because AP is prevalence-dependent and a composition change moves
both.

- **Primary metric:** AP in each universe, reported with its own prevalence, and
  the unpaired difference.
- **Secondary:** prevalence before/after, positives dropped, cohort-level shifts,
  ROC-AUC (prevalence-invariant, so it separates the composition effect from the
  ranking effect).
- **Reported regardless:** observations added/dropped, positive observations
  added/dropped, prevalence before/after, cohort-level changes, intersection size.

---

## Channel 2 — entity identity / present-day mappings

| | |
|---|---|
| **Strict-PIT arm** | SIC as filed, read from DERA `sub.sic` for that exact accession. FIRE exclusion applied to that value. Registrant identity is the CIK on the filing. |
| **Contaminated arm** | Present-day SIC — the SIC on the registrant's most recent submission — applied retroactively to every historical observation, with the FIRE exclusion applied to that value instead. |
| **Unit of analysis** | One 10-K observation. |
| **Observation membership changes?** | **Yes, but only via the FIRE flip**: an observation filed under a non-FIRE SIC whose registrant is classified 6000–6799 today leaves the universe, and vice versa. Observations whose SIC changes without crossing the FIRE boundary stay in and only change their industry-relative features. |
| **Pairing possible?** | Partially. Paired on the non-flipping majority; the flipping subset is a membership change and is reported separately, not forced into the paired estimand. |

**A scoping note, recorded before measurement.** CIK is the study's identity
(PIT contract requirement 3) and a CIK does not change. Ticker-map identity
errors therefore collapse into channel 1's survivorship mechanism rather than
forming an independent channel here. Registrant *name* drift has no effect on a
financial-ratio model, since no feature reads text. The only live mechanism left
in this channel is **SIC vintage**, and this protocol does not manufacture
others.

- **Primary metric:** signed ΔAP on the paired non-flipping subset.
- **Secondary:** count and label composition of the FIRE-flip subset; ROC-AUC.
- **Exposure gate (below) may kill this channel before any model is fitted.**

---

## Channel 3 — improper temporal evaluation / random splitting

| | |
|---|---|
| **Strict-PIT arm** | Frozen rolling historical evaluation, identical to Gate 2A: for cohort Y, train on every observation with cohort year < Y, test on cohort Y. No observation dated on or after the test cohort ever enters training. |
| **Contaminated arm** | Stratified random K-fold (**K = 5**, stratified on the label, seed 20260916) over the pooled 2012–2024 strict panel, ignoring both time and firm. Test predictions are pooled across folds. |
| **Held identical** | Feature set, model family, hyperparameters, tuning procedure (none), and the underlying eligible observation set. Only the split changes. |
| **Unit of analysis** | One 10-K observation. |
| **Observation membership changes?** | **No.** Both protocols evaluate the same 58,789 observations; only the assignment to train and test differs. |
| **Pairing possible?** | **Yes, on the observations both protocols place in a test fold** — under random K-fold every observation is tested exactly once, and under rolling evaluation every observation in cohorts ≥ 2013 is tested exactly once. Paired CIK-cluster bootstrap on that intersection. |

The estimand is the **evaluation-protocol effect**, not a model-selection
competition. Neither arm is tuned; the comparison is between two ways of
splitting the same data with the same model.

- **Primary metric:** signed ΔAP, contaminated minus strict, on the paired
  intersection.
- **Secondary:** ROC-AUC, score correlation, and the effect decomposed by
  whether the test observation had (a) a same-CIK training observation and
  (b) a strictly later-dated training observation.

**Quantified before any training** (this audit): usable observations, positives,
train/test overlap structure, and whether future observations can inform earlier
test predictions under the contaminated protocol.

---

## Minimum practically interesting effect

**±10% relative change in AP**, signed, consistent with the original design's
"below roughly 15%, 'evaluation was inflated' stops being an interesting claim"
and with the +10%/+15% alternatives Gate 2A was judged against.

Gate 2A measured the achievable precision of this panel: **MDE 24–33% relative**
for a *paired* design at 341 positives. Unpaired estimands will be materially
worse. Any channel whose plausible effect is below ~25% relative is therefore
unlikely to be resolvable on this panel regardless of exposure, and that
constraint is recorded here rather than discovered later.

## Statistical test / bootstrap design

- Paired estimands: CIK-cluster paired bootstrap, 2,000 replicates, seed
  20260916, percentile 95% intervals, `P(Δ > 0)` reported. Identical to Gate 2A.
- Unpaired estimands (channel 1 estimand B): independent CIK-cluster bootstrap
  in each arm, 2,000 replicates, difference taken across replicate pairs drawn
  independently. Correlation between arms is **not** assumed.
- Standard errors for any power statement are simulated under the null and power
  is evaluated at signed alternatives, as in `gate2_power_empirical.py`.

## Exposure gate — applied in this audit, before any modeling

Thresholds fixed in advance, and the recommendation depends only on exposure and
statistical feasibility, never on the expected direction of the result:

| recommendation | condition |
|---|---|
| **GO TO PILOT** | ≥ 30 positives affected **and** ≥ 1% of observations affected **and** a well-defined estimand (paired or unpaired) with adequate effective sample |
| **CONDITIONAL** | exposure present but marginal — 10–29 positives affected, or exposure 0.5–1% of observations, or the estimand is only definable unpaired at low effective sample |
| **KILL BEFORE MODELING** | < 10 positives affected **or** < 0.5% of observations affected, or no coherent estimand |

### Disclosed refinement to the feasibility clause (2026-09-16)

The GO criterion above requires "adequate effective sample" but did not put a
number on it. After the exposure counts were computed, and **before any Gate 2B
model was fitted**, that clause was operationalised in `gate2b_exposure.py` as a
projected-MDE ceiling: Gate 2A's measured MDE range (24-33% relative at 341
paired positives, pooled pairing variance reduction 0.878) is rescaled to each
estimand's effective sample, unpaired estimands additionally paying the
`1/sqrt(1 - 0.878)` = 2.86x penalty for losing the pairing.

    projected MDE > 100% relative  ->  KILL BEFORE MODELING
    projected MDE 40-100% relative ->  CONDITIONAL at best
    projected MDE <= 40% relative  ->  eligible for GO

This is recorded as a refinement, not a pre-registration: it was made with the
exposure numbers visible. It is one-directional by construction — it can only
move a channel toward caution, never toward GO — and it changed exactly one
verdict, downgrading survivor/universe from GO TO PILOT to CONDITIONAL.

**These MDE thresholds are a transparent decision refinement, not
pre-registered criteria.** They are reported as such wherever a verdict cites
them, and no result may be described as having met a pre-registered feasibility
bar.

## GO / CONDITIONAL / KILL rule for the pilots themselves

Applied only after a channel passes the exposure gate and its pilot is run,
mirroring the pre-registered Gate 2 rule:

- **GO** — the channel's effect is resolvable at the panel's measured dependence
  (power ≥ 0.80 at ±10% relative under the measured correlation).
- **CONDITIONAL** — resolvable only at the optimistic end of the measured
  dependence range.
- **KILL** — not resolvable even at the most favourable measured correlation.

A KILL verdict is a publishable negative finding, as in Gate 2A, and does not
license changing the channel's definition to obtain a different answer.

---

## Amendment 1 — final channel decisions and a correction (2026-09-20)

Decisions taken after the exposure audit, recorded before the temporal pilot was
run.

### Correction: what the temporal pilot is and is not powered for

An earlier reading of this protocol could suggest that channel 3 clears the
±10% relative bar. **It does not, and must not be described that way.**

> Temporal evaluation cannot currently be described as capable of resolving
> effects at the ±10% relative scale. Its projected MDE is approximately
> **25–34% relative**.

The reasons for proceeding are therefore feasibility and exposure, not adequate
power at the minimum interesting effect:

- nearly complete dataset exposure — 100% of observations touched;
- **317 paired positives**, the largest effective sample of any channel here;
- extensive repeated-CIK exposure — 8,184 of 9,466 CIKs appear more than once,
  and 97.8% of rows belong to a repeating CIK;
- approximately **80.3%** expected future-same-CIK training contamination under
  random K = 5;
- sufficient feasibility to determine whether the actual temporal-evaluation
  distortion is *large*.

**The pilot tests whether the effect is large enough to justify the full
experiment. It does not claim adequate power for a 10% effect.** A null or small
result from it bounds the effect only loosely, and must be reported with that
limitation attached.

The post-exposure MDE thresholds in the section above are retained as a
**transparent decision refinement, not pre-registered criteria**.

### Channel 2 — entity identity: KILL BEFORE MODELING

Positive-class exposure is negligible: 4,248 observations with a SIC change, but
only **2 positives affected**, and **1 positive** affected by a FIRE universe
flip. Not modelled further.

Preserved as an **exposure-audit result**: historical SIC vintage matters
operationally for a non-trivial minority of observations (7.2%, 1,074 CIKs, and
516 observations that would leave the universe under today's SIC), but it has
insufficient positive-class exposure to support a bankruptcy-performance
experiment. That is a statement about statistical reach, not about whether SIC
vintage is a real data-management concern.

### Channel 1A — survivor common-intersection AP effect: CONDITIONAL, no pilot

With 76 positives in the survivor universe and a projected relative MDE of
roughly **51–70%**, the paired AP experiment is too weak for the ±10% minimum
interesting effect. Status stays CONDITIONAL. No modelling effort is spent on it
unless later evidence gives a compelling reason.

### Channel 1B — survivor benchmark composition: structural finding, no AP model

Treated as a **structural benchmark-composition finding**, not as an
underpowered predictive-performance hypothesis. The exposure audit alone
establishes it:

| quantity | strict PIT | survivor universe |
|---|---|---|
| observations | 58,789 | 37,866 |
| positives | 341 | 76 |
| prevalence | 0.00580 | 0.00201 |

- **35.6%** of observations removed; **77.7%** of positives removed;
- prevalence reduction **65.4%**.

These are preserved as descriptive results. **No significance test is computed
for 1B**, because there is no inferential question here that the counts do not
already answer, and manufacturing one would add an unearned inferential veneer.
**No AP model is fitted for 1B at this stage.**

Two precision requirements attach to every use of this finding:

1. **Name the mechanism exactly.** The contamination is a *present-day-survivor
   universe defined by filing activity in 2024*. It is not survivorship bias in
   general, and it may not be generalised to every possible form of
   survivorship bias — delisting, index membership, ticker-map coverage, data
   vendor back-fill and acquisition all behave differently.
2. **Retain the cohort truncation caveat.** Survivor filtering is strongest in
   the early cohorts and weakens mechanically toward 2024: 61% of 2012
   observations are removed, 8.8% of 2023, and **0% of 2024 — because a
   registrant that filed a 10-K in 2024 necessarily satisfies the 2024-filer
   condition.** The magnitude of this channel is therefore partly an artifact of
   how much time has elapsed, not only of firm mortality.

### Channel 3 — temporal evaluation: GO TO PILOT

Minimum three-cohort pilot only, on the already-selected cohorts **2017, 2015,
2023**, under the same strict validation-CIK exclusion. Financial ratios only;
identical feature definitions and one fixed model family in both arms; no text,
LLM or macro features; no new model search. The full 2012–2024 experiment is not
run.

**Arm A — strict temporal.** For test cohort Y, train only on observations from
cohort years < Y.

**Arm B — random K = 5.** The same eligible observations and feature
definitions, with observations assigned at random to five folds, so future
firm-years and future population information can enter training for earlier
observations. Each observation is scored when its own fold is held out, and the
cohort's AP is computed on exactly the rows Arm A tests. **Observations are not
grouped by CIK in Arm B**, because same-CIK future leakage is part of the
contamination mechanism being measured. Seed **20260920**, frozen before any
result was seen and recorded here.

**Pre-declared diagnostic, one only: random K = 5 grouped by CIK.** Not a second
primary contamination arm. Its sole purpose is to separate (1) future same-firm
leakage from (2) broader future-population / temporal-regime leakage, by
comparing strict temporal, random observation-level K = 5, and CIK-grouped
K = 5 under the same features and model. No further ablations are added after
results are seen.

### Decision rule after the temporal pilot

The sign is not required to be positive. Magnitude is interpreted against
measured feasibility, not by mechanically thresholding a point estimate:

- **candidate for full experiment** — large and reproducible effect, roughly
  ≥ 25% relative AP change, with consistent evidence across cohorts and the
  diagnostic;
- **CONDITIONAL / descriptive** — moderate effect below the currently detectable
  range;
- **KILL** — negligible effect, with intervals excluding practically large
  distortions where the data permit that conclusion.

---

## Amendment 2 — channel 3 promoted to full characterization (2026-09-20)

Channel 3 is accepted as **CONDITIONAL GO TO FULL CHARACTERIZATION, not a
confirmatory GO.**

1. **The three-cohort pilot estimated a +14.7% pooled relative AP change**
   (pooled ΔAP +0.0034, paired bootstrap 95% CI [+0.0000, +0.0121],
   P(ΔAP>0) = 0.978), positive in all three cohorts and in both split variants.
   **The pilot does not prove a +14.7% effect** and must never be described as
   having done so. It establishes direction and mechanism credibly and magnitude
   poorly.
2. **The full 12-cohort design remains underpowered for a 10–15% relative
   effect.** At the measured paired dependence (bootstrap AP correlation 0.96)
   and 317 positives, MDE is ≈ 25.6% relative; power is 0.195 at +10%, 0.375 at
   +15%, and 0.363 at the pilot's own observed +14.7%.
3. **The full experiment is therefore an effect-estimation and heterogeneity
   analysis, not a binary significance hunt.** It will estimate signed effect
   size, its uncertainty, and temporal heterogeneity across cohorts.
4. **Statistical significance is not the sole success criterion.** Sign
   consistency across cohorts, stability of the aggregate under different
   aggregation rules, whether any single cohort dominates, and the grouped-CIK
   mechanism comparison all carry evidential weight alongside interval coverage.
5. **No further model, feature, split, bootstrap or contamination-definition
   changes are allowed after this amendment.** The frozen setup is: strict
   validation-CIK exclusion; financial ratios only; one fixed
   `LogisticRegression` (`C=1.0`, `class_weight="balanced"`, `solver="lbfgs"`,
   `max_iter=5000`), no hyperparameter search; identical feature definitions and
   preprocessing in every arm; arm A strict temporal (train on cohort years
   < Y); arm B random observation-level K=5 at split seed **20260920**;
   the single pre-declared CIK-grouped K=5 diagnostic at the same seed;
   paired CIK-cluster bootstrap, 2,000 replicates, seed **20260916**. No new
   ablations.

Scope of the full run: every rolling-testable cohort, **2013–2024** (2012 has no
earlier training fold). Aggregates will be reported as a set — pooled
observation-level, cohort-level median, cohort-level mean, sign counts,
event-weighted, and bootstrap uncertainty — never as a single pooled number.
Heterogeneity diagnostics (ΔAP by year, and its relation to training positives,
baseline AP and the fraction of future training observations) are **descriptive
only**; no post-hoc model is fitted to explain them.

The grouped-CIK diagnostic answers exactly one question — does removing all
same-CIK overlap materially reduce the effect — and does not become a primary
arm.
