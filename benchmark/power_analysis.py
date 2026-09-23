"""Gate 2: can the study resolve a protocol difference, and at what assumption?

Reports both estimands across a grid of score correlations, because the paired
design is the only reason the study is affordable and its correlation is
currently a guess.

Decision rule:

    GO           useful at correlation 0.70
    CONDITIONAL  only useful at 0.90 or above
    KILL         not useful even at 0.95

Replace EVENT_LEVELS with the real vector from Gate 1 and rerun. Replace the
correlation grid with the measured value once the first real models exist.

    python3 power_analysis.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from constants import DEFAULT_AP_PIT, DEFAULT_FIRM_ICC, RANDOM_SEED
from panel_simulation import PanelSpec, evaluate_design

# 2012 through 2024: cohorts with non-size-biased XBRL coverage and a fully
# observed 365-day outcome window as of September 2026.
N_MATURE_FOLDS = 13

# Credit-cycle shape normalised to a mean of one event, scaled per level.
CYCLE_SHAPE = (
    0.85, 0.70, 0.60, 0.75, 1.05, 0.80, 0.70, 0.75, 2.30, 1.30, 0.85, 0.75, 0.80,
)

PREVALENCE = 0.01
REFERENCE_DELTA = 0.05
EVENT_LEVELS = (25, 40, 60)
CORRELATION_GRID = (0.50, 0.70, 0.90, 0.95)

# Relative inflation worth reporting in an abstract. Below roughly 15%,
# "evaluation was inflated" stops being an interesting claim.
REFERENCE_RELATIVE_EFFECT = 0.15

OUTPUT_PATH = Path("power_grid.csv")


def build_panel(mean_events: int) -> PanelSpec:
    return PanelSpec(
        fold_positive_counts=tuple(
            max(5, int(round(mean_events * factor))) for factor in CYCLE_SHAPE
        ),
        prevalence=PREVALENCE,
    )


def run_grid() -> list[dict]:
    rows: list[dict] = []
    for mean_events in EVENT_LEVELS:
        panel = build_panel(mean_events)
        for correlation in CORRELATION_GRID:
            result = evaluate_design(
                panel=panel,
                ap_pit=DEFAULT_AP_PIT,
                reference_delta=REFERENCE_DELTA,
                correlation=correlation,
                firm_icc=DEFAULT_FIRM_ICC,
                seed=RANDOM_SEED,
            )
            rows.append(
                {
                    "mean_events": mean_events,
                    "total_events": panel.total_positives,
                    "correlation": correlation,
                    "se_absolute": round(result.se_absolute, 4),
                    "mde_absolute": round(result.mde_absolute, 4),
                    "se_relative_pct": round(100 * result.se_relative, 1),
                    "mde_relative_pct": round(100 * result.mde_relative, 1),
                    "power_abs_005": round(result.power_at_absolute(0.05), 3),
                    "power_rel_15pct": round(
                        result.power_at_relative(REFERENCE_RELATIVE_EFFECT), 3
                    ),
                }
            )
            print(f"done events={mean_events} rho={correlation}", flush=True)
    return rows


def print_table(rows: list[dict]) -> None:
    headers = list(rows[0].keys())
    widths = {header: max(len(header), 9) for header in headers}
    print(" | ".join(header.rjust(widths[header]) for header in headers))
    print("-+-".join("-" * widths[header] for header in headers))
    for row in rows:
        print(" | ".join(str(row[header]).rjust(widths[header]) for header in headers))


def main() -> None:
    rows = run_grid()
    print()
    print_table(rows)
    with OUTPUT_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
