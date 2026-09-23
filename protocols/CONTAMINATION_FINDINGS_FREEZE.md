# Contamination Findings — FROZEN

**Date:** 2026-09-20
**Freeze commit:** `63efd1b`

> **This file freezes the contamination analysis. These channels are not to be
> modified or extended after this commit unless a new study is explicitly
> opened.** No further contamination experiments will be added.

The contamination programme asked how much a bankruptcy-prediction evaluation is
inflated when run under contaminated conventions instead of point-in-time ones.
Four channels were specified, measured and closed. Effects were treated as
signed throughout; none was assumed to improve performance.

---

## 1. Later / restated financials — negative/null performance result

**Status: KILL** for the pre-registered inflation hypothesis.
**Detail:** `GATE2A_RESULT.md`

Preferring restated facts over as-filed ones did **not** inflate average
precision. Under strict validation-CIK exclusion the pooled effect was
**negative**: ΔAP −0.0025, **−10.49% relative**, paired bootstrap 95% CI
[−0.0152, +0.0010], P(ΔAP>0) = 0.123.

**There is no evidence for the pre-registered +10%/+15% inflation hypothesis.**
At the measured correlation range 0.92–0.95 the empirical MDE was 24–33%
relative and power at +15% was 0.25–0.43, so the pre-registered rule returned
KILL. The design-stage assumptions were wrong in three of four places: AP under
strict PIT 0.15 assumed against 0.0235 measured, firm ICC 0.30 against 0.52, and
a +15% reference effect against −10.5% observed.

The mechanism is identified and is the substantive contribution here: **a
registrant that files Chapter 7/11 stops filing, so its last 10-K is never
restated.** Restatement therefore acts almost entirely on survivors — differing
for 14.8–36.1% of positives against 24.6–57.8% of negatives — and under
contamination the positives' mean rank *falls*. This stands in the paper as an
informative negative/null channel.

## 2. Present-day survivor universe — structural benchmark-composition result

**Status: structural finding. No powered AP effect is claimed.**
**Detail:** `GATE2B_PROTOCOL.md` Amendment 1

| quantity | strict PIT | survivor universe |
|---|---|---|
| observations | 58,789 | 37,866 |
| positives | 341 | 76 |
| prevalence | 0.00580 | 0.00201 |

- **35.6% of observations removed**
- **77.7% of positives removed**
- **prevalence 0.00580 → 0.00201**
- **65.4% prevalence reduction**

**No powered AP effect is claimed for this channel, and no significance test was
computed.** The common-intersection AP estimand (1A) retains only 76 positives
with a projected relative MDE of 51–70%, so it was left CONDITIONAL and never
piloted; the composition estimand (1B) is unpaired by construction with a
projected MDE of 69–94%. The counts above are the result.

Two precision requirements attach to every use of this finding:

1. **The mechanism is exactly a present-day-survivor universe defined by filing
   activity in 2024.** It is not survivorship bias in general and must not be
   generalised to delisting, index membership, ticker-map coverage, vendor
   back-fill or acquisition, which behave differently.
2. **Cohort truncation is intrinsic.** Survivor filtering is strongest in early
   cohorts and weakens mechanically toward the end of the window: 61% of 2012
   observations removed, 8.8% of 2023, and **0% of 2024**, because a registrant
   that filed a 10-K in 2024 necessarily satisfies the 2024-filer condition. Part
   of this channel's magnitude is elapsed time, not firm mortality.

## 3. Entity / SIC vintage — KILL BEFORE MODELING

**Status: KILL BEFORE MODELING.**
**Detail:** `GATE2B_PROTOCOL.md` Amendment 1

Operational exposure exists and is not trivial: 4,248 observations (7.2%) carry a
SIC that differs from the registrant's present-day SIC, 3,880 change 2-digit
group, 1,074 CIKs are affected, 516 observations would leave the universe under
today's SIC and 1,042 would enter.

**But only two positives are affected**, and only one by a FIRE universe flip.
That is far below any threshold at which a bankruptcy-performance experiment
could say anything, so the channel was killed before a model was fitted.

Preserved as an exposure-audit result: **historical SIC vintage matters
operationally for a minority of observations but has insufficient positive-class
exposure for a performance experiment.** That is a statement about statistical
reach, not about whether SIC vintage is a real data-management concern — it is.

Scoping note carried forward: CIK is the study's identity and never changes, so
ticker-map identity errors belong to channel 2 above rather than here, and
registrant name drift cannot move a ratio-only model.

## 4. Temporal evaluation — evaluation-protocol sensitivity

**Status: sensitivity result, not stable leakage inflation.**
**Detail:** `GATE2B_CHANNEL3_RESULT.md`, `GATE2C_RESULT.md`

Random observation-level K=5 against strict rolling evaluation, 12 cohorts:
8 of 12 positive, heterogeneous, **event-weighted +2.6% relative**, paired
bootstrap 95% CI [−0.0036, +0.0084], P(ΔAP>0) = 0.755. Aggregate estimators
disagree by a factor of six (+2.6% event-weighted to +16.2% pooled
observation-level), and 2024 alone moves the event-weighted aggregate by 7.2
percentage points.

- **Same-CIK grouping does not resolve the differences.** The pre-declared
  grouped diagnostic drove same-CIK training overlap from 79.6% to 0% and left
  the effect marginally larger (+4.17% grouped against +2.59% ungrouped, sign
  preserved in 11 of 12 cohorts). Same-CIK overlap is **not supported as the
  dominant mechanism**, and this is strong evidence against it.
- **Training-volume matching eliminates the typical-cohort directional effect**
  and leaves heterogeneous cohort-specific differences. With training N and
  positive count held exactly fixed over 100 frozen draws per cohort, the cohort
  median relative effect falls from **+11.87% to +0.04%**, the sign split becomes
  **6 positive / 5 negative / 1 exactly zero**, and the effect does not track
  future exposure (Spearman **+0.175**). The 2024 structural control returns
  **exactly 0** with zero variance.
- **Future-population exposure is not supported as the dominant mechanism**
  either. Neither mechanism is claimed to be universally or causally excluded:
  these are two designs on one panel of 341 positives, bounding dominance rather
  than existence.
- **The residual differences are best described as cohort-specific
  training-composition sensitivity.**

---

## What the contamination programme established

Across four channels the study found **no stable, powered performance-inflation
effect** from any single contaminated convention it could measure. What it did
establish is sharper and, in places, counter to the field's working assumptions:

1. Restatement contamination does not inflate bankruptcy-prediction AP, and there
   is a clean structural reason why — failed registrants stop filing.
2. Survivor-universe construction is a **composition** problem of large
   magnitude (77.7% of positives), not a subtle scoring problem.
3. Historical classification vintage is an operational data-management concern
   without enough positive-class exposure to be a performance question here.
4. Protocol choice (rolling against random splitting) produces differences that
   are real but unstable, and the standard remedy — grouping by firm — does not
   address them.

The honest summary is that **this panel's 341 positives cannot resolve
contamination effects at the ±10% relative scale**, which is itself a
methodological finding about what feasibility the field's leakage claims require.
