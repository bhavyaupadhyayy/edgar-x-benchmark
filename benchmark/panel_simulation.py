"""Panel simulator for the paired protocol comparison.

Estimand (primary):

    delta_AP = sum_k w_k * [ AP_k(contaminated) - AP_k(point-in-time) ]
    w_k = positives in fold k / total positives

Event weighting, not the equal-weighted mean of annual deltas. Bankruptcies
cluster in credit cycles, so annual folds differ in event count by an order of
magnitude and equal weighting throws away precision.

Panel model. A pool of firms carries persistent effects u_j that are shared
across folds. In each fold a subset is observed, a fold-specific subset of
those goes bankrupt, and bankrupt firms are removed from the pool. Bankruptcy
is absorbing: no firm can be positive twice. A churn fraction of survivors is
replaced each fold to represent exits and new registrants.

Two arms score the same observations. Their score noise is correlated, which is
what makes the paired comparison affordable; that correlation is the single
most important assumption in the whole exercise.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

from constants import (
    ALPHA,
    CALIBRATION_DRAWS,
    DEFAULT_FIRM_CHURN_RATE,
    MDE_Z_MULTIPLIER,
    MONTE_CARLO_REPLICATES,
)


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    """Average precision. Hot path, called millions of times by the sweep."""
    order = np.argsort(-scores, kind="stable")
    ranked = labels[order]
    cumulative_hits = np.cumsum(ranked)
    ranks = np.arange(1, ranked.size + 1)
    return float(((cumulative_hits / ranks) * ranked).sum() / cumulative_hits[-1])


@dataclass(frozen=True)
class PanelSpec:
    """Shape of the whole evaluation panel, one entry per temporal fold."""

    fold_positive_counts: tuple[int, ...]
    prevalence: float

    @property
    def n_folds(self) -> int:
        return len(self.fold_positive_counts)

    @property
    def total_positives(self) -> int:
        return sum(self.fold_positive_counts)

    @property
    def fold_sizes(self) -> tuple[int, ...]:
        return tuple(
            int(round(count / self.prevalence)) for count in self.fold_positive_counts
        )

    @property
    def event_weights(self) -> np.ndarray:
        counts = np.array(self.fold_positive_counts, dtype=float)
        return counts / counts.sum()


@dataclass(frozen=True)
class PowerResult:
    """Sampling behaviour of both estimands under one design.

    Two statistics, each simulated directly so each carries its own standard
    error:

      absolute  D = sum_k w_k (AP_con_k - AP_pit_k)
      relative  R = sum_k w_k (AP_con_k - AP_pit_k) / sum_k w_k AP_pit_k

    R is a ratio of event-weighted sums, not an average of per-fold ratios. The
    per-fold ratio form lets one quiet year with an accidentally low PIT AP
    dominate the whole statistic; the ratio-of-sums form does not.
    """

    panel: PanelSpec
    ap_pit: float
    correlation: float
    mean_absolute: float
    se_absolute: float
    mean_relative: float
    se_relative: float

    @property
    def mde_absolute(self) -> float:
        return MDE_Z_MULTIPLIER * self.se_absolute

    @property
    def mde_relative(self) -> float:
        """MDE on the ratio statistic, with its own simulated uncertainty."""
        return MDE_Z_MULTIPLIER * self.se_relative

    def power_at_absolute(self, true_delta: float) -> float:
        return _normal_power(true_delta, self.se_absolute)

    def power_at_relative(self, true_ratio: float) -> float:
        return _normal_power(true_ratio, self.se_relative)


def _normal_power(effect: float, standard_error: float) -> float:
    """Normal-approximation power. A design-stage approximation, not a formal
    power calculation: average precision is nonlinear and small-sample skewed,
    so manuscript numbers should come from direct rejection rates under
    simulated null and alternative, not from plugging an SE into this.
    """
    z_critical = norm.ppf(1 - ALPHA / 2)
    standardized = effect / standard_error
    return float(
        norm.sf(z_critical - standardized) + norm.cdf(-z_critical - standardized)
    )


def calibrate_separation(
    target_ap: float,
    n_positive: int,
    fold_size: int,
    seed: int,
    n_draws: int = CALIBRATION_DRAWS,
) -> float:
    """Positive-class mean shift that yields a target AP in expectation.

    Averaged over many noise draws. Calibrating against a single draw makes the
    simulated true effect a function of the seed, which at small event counts
    swamps the effect being studied.
    """
    rng = np.random.default_rng(seed)
    labels = _labels_for(n_positive, fold_size)
    noise = rng.standard_normal((n_draws, fold_size))

    def expected_ap_gap(mu: float) -> float:
        scores = mu * labels + noise
        realized = [average_precision(labels, row) for row in scores]
        return float(np.mean(realized)) - target_ap

    return float(brentq(expected_ap_gap, 0.0, 12.0, xtol=1e-4))


def simulate_estimands(
    panel: PanelSpec,
    mu_pit: float,
    mu_contaminated: float,
    correlation: float,
    firm_icc: float,
    churn_rate: float = DEFAULT_FIRM_CHURN_RATE,
    duplicate_positive_rate: float = 0.0,
    n_replicates: int = MONTE_CARLO_REPLICATES,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Draw both the absolute and the relative estimator repeatedly."""
    rng = np.random.default_rng(seed)
    weights = panel.event_weights
    absolute = np.empty(n_replicates)
    relative = np.empty(n_replicates)

    for replicate in range(n_replicates):
        fold_ap_pit, fold_ap_con = _simulate_one_panel(
            panel=panel,
            mu_pit=mu_pit,
            mu_contaminated=mu_contaminated,
            correlation=correlation,
            firm_icc=firm_icc,
            churn_rate=churn_rate,
            duplicate_positive_rate=duplicate_positive_rate,
            rng=rng,
        )
        weighted_pit = float(np.dot(weights, fold_ap_pit))
        weighted_gap = float(np.dot(weights, fold_ap_con - fold_ap_pit))
        absolute[replicate] = weighted_gap
        relative[replicate] = weighted_gap / weighted_pit

    return absolute, relative


def evaluate_design(
    panel: PanelSpec,
    ap_pit: float,
    reference_delta: float,
    correlation: float,
    firm_icc: float,
    churn_rate: float = DEFAULT_FIRM_CHURN_RATE,
    duplicate_positive_rate: float = 0.0,
    n_replicates: int = MONTE_CARLO_REPLICATES,
    seed: int = 0,
) -> PowerResult:
    """Standard errors and minimum detectable effects for one design cell.

    Separation is calibrated on the median fold so a single pair of shifts
    applies panel-wide, matching the assumption that the underlying signal is
    stable across cohorts even though event counts are not.
    """
    median_positives = int(np.median(panel.fold_positive_counts))
    median_size = int(round(median_positives / panel.prevalence))

    mu_pit = calibrate_separation(ap_pit, median_positives, median_size, seed + 1)
    mu_contaminated = calibrate_separation(
        min(ap_pit + reference_delta, 0.95), median_positives, median_size, seed + 1
    )
    absolute, relative = simulate_estimands(
        panel=panel,
        mu_pit=mu_pit,
        mu_contaminated=mu_contaminated,
        correlation=correlation,
        firm_icc=firm_icc,
        churn_rate=churn_rate,
        duplicate_positive_rate=duplicate_positive_rate,
        n_replicates=n_replicates,
        seed=seed + 2,
    )
    return PowerResult(
        panel=panel,
        ap_pit=ap_pit,
        correlation=correlation,
        mean_absolute=float(absolute.mean()),
        se_absolute=float(absolute.std(ddof=1)),
        mean_relative=float(relative.mean()),
        se_relative=float(relative.std(ddof=1)),
    )


def _simulate_one_panel(
    panel: PanelSpec,
    mu_pit: float,
    mu_contaminated: float,
    correlation: float,
    firm_icc: float,
    churn_rate: float,
    duplicate_positive_rate: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """One realisation of the panel, returning per-fold AP for both arms."""
    pool_size = max(panel.fold_sizes)
    firm_pit, firm_con = _correlated_normals(
        rng, pool_size, correlation, scale=np.sqrt(firm_icc)
    )
    alive = np.arange(pool_size)
    fold_ap_pit = np.empty(panel.n_folds)
    fold_ap_con = np.empty(panel.n_folds)

    for fold_index, (n_positive, fold_size) in enumerate(
        zip(panel.fold_positive_counts, panel.fold_sizes)
    ):
        observed = rng.choice(alive, size=fold_size, replace=False)
        labels = np.zeros(fold_size)
        positive_slots = rng.choice(fold_size, size=n_positive, replace=False)
        labels[positive_slots] = 1.0

        # One bankruptcy can label more than one 10-K when two filings fall
        # less than a horizon apart. Duplicated positives share a firm, so they
        # share the persistent effect and are not independent events. Modelled
        # by pointing the duplicated slots at an already-positive firm.
        n_duplicated = int(round(duplicate_positive_rate * n_positive))
        if n_duplicated:
            duplicated = positive_slots[-n_duplicated:]
            sources = positive_slots[:n_duplicated]
            observed[duplicated] = observed[sources]

        within_pit, within_con = _correlated_normals(
            rng, fold_size, correlation, scale=np.sqrt(1.0 - firm_icc)
        )
        scores_pit = mu_pit * labels + firm_pit[observed] + within_pit
        scores_con = mu_contaminated * labels + firm_con[observed] + within_con
        fold_ap_pit[fold_index] = average_precision(labels, scores_pit)
        fold_ap_con[fold_index] = average_precision(labels, scores_con)

        alive = _advance_pool(
            alive=alive,
            bankrupt=observed[positive_slots],
            churn_rate=churn_rate,
            firm_pit=firm_pit,
            firm_con=firm_con,
            correlation=correlation,
            firm_icc=firm_icc,
            rng=rng,
        )

    return fold_ap_pit, fold_ap_con


def _advance_pool(
    alive: np.ndarray,
    bankrupt: np.ndarray,
    churn_rate: float,
    firm_pit: np.ndarray,
    firm_con: np.ndarray,
    correlation: float,
    firm_icc: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Retire bankrupt firms, churn some survivors, and refresh their effects.

    Firm slots are recycled rather than grown, so the pool stays a fixed size.
    A recycled slot receives a fresh persistent effect, which is what makes it
    a different firm.
    """
    retired = set(bankrupt.tolist())
    survivors = np.array([firm for firm in alive if firm not in retired])

    n_churned = int(round(churn_rate * survivors.size))
    if n_churned:
        churned = rng.choice(survivors, size=n_churned, replace=False)
        retired.update(churned.tolist())

    recycled = np.fromiter(retired, dtype=int, count=len(retired))
    if recycled.size:
        fresh_pit, fresh_con = _correlated_normals(
            rng, recycled.size, correlation, scale=np.sqrt(firm_icc)
        )
        firm_pit[recycled] = fresh_pit
        firm_con[recycled] = fresh_con

    return alive


def _labels_for(n_positive: int, fold_size: int) -> np.ndarray:
    labels = np.zeros(fold_size)
    labels[:n_positive] = 1.0
    return labels


def _correlated_normals(
    rng: np.random.Generator, size: int, correlation: float, scale: float
) -> tuple[np.ndarray, np.ndarray]:
    shared = rng.standard_normal(size)
    independent = rng.standard_normal(size)
    partner = correlation * shared + np.sqrt(1.0 - correlation**2) * independent
    return shared * scale, partner * scale
