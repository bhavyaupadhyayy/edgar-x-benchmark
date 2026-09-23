"""Shared loading and style for EDGAR-X publication figures.

Reads ONLY the frozen tracked release artifacts. No experiment is rerun and no
number is recomputed from predictions; every value plotted is taken from
`gate4_release/*.csv` as committed at dcee103.
"""
from pathlib import Path
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "benchmark/gate4_release"
OUT = ROOT / "paper/figures"

ARMS = ("A_ratios", "B_text", "C_combined")
LABELS = {"A_ratios": "Ratios", "B_text": "Text", "C_combined": "Ratios + Text"}
# Readability first: distinguishable in greyscale and to common colour-vision
# deficiencies; no decorative styling.
COLOURS = {"A_ratios": "#4C4C4C", "B_text": "#1F6FB4", "C_combined": "#C1471B"}
MARKERS = {"A_ratios": "o", "B_text": "s", "C_combined": "^"}

plt.rcParams.update({
    # Type 42 (TrueType) rather than Matplotlib's default Type 3, which many
    # publishers reject and which is not searchable or selectable.
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "figure.dpi": 150, "savefig.dpi": 300, "font.size": 9,
    "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "figure.constrained_layout.use": True,
})


def cohorts(population="B"):
    rows = [r for r in csv.DictReader((RELEASE / "cohort_metrics.csv").open())
            if r["population"] == population]
    rows.sort(key=lambda r: int(r["cohort_year"]))
    return rows


def aggregates(population="B"):
    return {r["quantity"]: r for r in
            csv.DictReader((RELEASE / "aggregate_metrics.csv").open())
            if r["population"] == population}


def save(fig, stem):
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{stem}.{ext}", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {stem}.pdf and {stem}.png")
