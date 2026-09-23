"""Figure 2: average precision by test cohort, 2013-2024, for all three arms."""
import matplotlib.pyplot as plt
from _common import ARMS, COLOURS, LABELS, MARKERS, aggregates, cohorts, save

rows = cohorts("B")
years = [int(r["cohort_year"]) for r in rows]
agg = aggregates("B")

fig, (ax, axn) = plt.subplots(2, 1, figsize=(5.8, 4.3), height_ratios=[3.1, 1],
                              sharex=True)
for arm in ARMS:
    ax.plot(years, [float(r[f"ap_{arm}"]) for r in rows],
            marker=MARKERS[arm], color=COLOURS[arm], linewidth=1.6,
            markersize=4.5, label=LABELS[arm])
    ax.axhline(float(agg[f"ap_{arm}"]["event_weighted"]), color=COLOURS[arm],
               linewidth=0.9, linestyle=":", alpha=0.85)

ax.set_ylabel("Average precision")
ax.legend(loc="upper left", frameon=False, ncol=3, fontsize=8.0,
          borderaxespad=0.3, columnspacing=1.4)
ax.axvspan(2020.6, 2021.4, color="#BBBBBB", alpha=0.18, zorder=0)
ax.annotate("2021: 5 positive obs.;\nper-cohort AP is unstable",
            xy=(2021, float(rows[years.index(2021)]["ap_C_combined"])),
            xytext=(2013.3, 0.345), fontsize=7.2, ha="left",
            arrowprops=dict(arrowstyle="->", linewidth=0.8, color="#666666"))

axn.bar(years, [int(r["positives"]) for r in rows], color="#999999", width=0.62)
axn.set_ylabel("Positive obs.")
axn.axvspan(2020.6, 2021.4, color="#BBBBBB", alpha=0.18, zorder=0)
axn.set_xlabel("Test cohort (10-K acceptance year)")
axn.set_xticks(years)
for y, r in zip(years, rows):
    axn.text(y, int(r["positives"]) + 1.2, r["positives"], ha="center", fontsize=6.6)
axn.set_ylim(0, 72)
save(fig, "fig2_ap_by_cohort")
