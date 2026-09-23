"""Figure 3: per-cohort incremental value of text over ratios (B - A)."""
import matplotlib.pyplot as plt
import numpy as np
from _common import aggregates, cohorts, save

rows = cohorts("B")
years = [int(r["cohort_year"]) for r in rows]
delta = np.array([float(r["delta_B_text_vs_A_ratios"]) for r in rows])
lo = np.array([float(r["ci_lo_B_text_vs_A_ratios"]) for r in rows])
hi = np.array([float(r["ci_hi_B_text_vs_A_ratios"]) for r in rows])
p = np.array([float(r["p_gt0_B_text_vs_A_ratios"]) for r in rows])
ew = float(aggregates("B")["delta_B_text_vs_A_ratios"]["event_weighted"])

fig, ax = plt.subplots(figsize=(5.8, 3.6))
x = np.arange(len(years))
excludes_zero = lo > 0
ax.errorbar(x[excludes_zero], delta[excludes_zero],
            yerr=[delta[excludes_zero] - lo[excludes_zero],
                  hi[excludes_zero] - delta[excludes_zero]],
            fmt="s", color="#1F6FB4", markersize=5, capsize=3, linewidth=1.2,
            label="95% interval excludes zero")
ax.errorbar(x[~excludes_zero], delta[~excludes_zero],
            yerr=[delta[~excludes_zero] - lo[~excludes_zero],
                  hi[~excludes_zero] - delta[~excludes_zero]],
            fmt="o", color="#8FB8DA", markersize=5, capsize=3, linewidth=1.2,
            markerfacecolor="white", label="interval includes zero")
ax.axhline(0, color="#333333", linewidth=1.0)
ax.axhline(ew, color="#C1471B", linewidth=1.1, linestyle="--", zorder=0,
           label=f"event-weighted ΔAP = +{ew:.4f}")
ax.set_xticks(x); ax.set_xticklabels(years)
ax.set_xlabel("Test cohort"); ax.set_ylabel("ΔAP  (text − ratios)")
ax.axvspan(x[years.index(2021)] - 0.45, x[years.index(2021)] + 0.45,
           color="#BBBBBB", alpha=0.18, zorder=0)
ax.text(x[years.index(2021)], 0.845, "2021: 5 positive obs.", fontsize=6.8,
        ha="center", color="#555555")
for xi, d, hv, pv in zip(x, delta, hi, p):
    ax.text(xi, hv + 0.030, f"P={pv:.2f}", ha="center", fontsize=6.3, color="#555555")
ax.set_ylim(-0.12, 0.88)
ax.legend(loc="upper left", frameon=False, fontsize=7.6)
save(fig, "fig3_text_increment")
