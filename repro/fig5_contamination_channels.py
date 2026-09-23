"""Figure 5: contamination channels do not share an estimand.

Deliberately NOT a single numeric axis. Each panel carries the quantity that is
actually defined for that channel; the figure's point is that these quantities
are not commensurable and must not be averaged. Values are transcribed from the
frozen result documents at dcee103.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Match the other figures: 300 dpi raster export, no decorative styling.
plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42,
                     "savefig.dpi": 300, "font.size": 9,
                     "axes.titlesize": 10, "axes.labelsize": 9})

# Constrained layout collapses with the sub-axis caption rows used here, so
# spacing is set explicitly and the engine is never enabled for this figure.
fig = plt.figure(figsize=(5.8, 5.4), layout=None)
axes = [fig.add_subplot(2, 2, i + 1) for i in range(4)]
for ax in axes:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)

# --- 1. restatement: signed ABSOLUTE AP effect, with its own interval -------
# The point estimate and the 95% interval are both absolute AP, so they share a
# scale. The relative figure and the pre-measurement band are relative and are
# therefore reported as text, never plotted on this axis. No interval is
# recomputed: both values are transcribed from the frozen result document.
ax = axes[0]
ax.errorbar([-0.0025], [0], xerr=[[0.0127], [0.0035]], fmt="s", color="#C1471B",
            markersize=6, capsize=4, linewidth=1.4)
ax.axvline(0, color="#333333", linewidth=1.0)
ax.text(-0.0025, 0.30, "ΔAP = −0.0025", ha="center", fontsize=7.4,
        fontweight="bold")
ax.text(-0.0068, -0.34, "95% CI [−0.0152, +0.0010]", ha="center", fontsize=6.3)
ax.text(-0.0068, -0.78, "−10.49% relative; hypothesis fixed\nin advance was +10 to +15% relative",
        ha="center", fontsize=6.3, color="#444444")
ax.set_xlim(-0.020, 0.007); ax.set_ylim(-0.95, 0.75); ax.set_yticks([])
ax.set_xticks([-0.015, -0.010, -0.005, 0.0, 0.005])
ax.tick_params(axis="x", labelsize=6.8)
ax.set_xlabel("absolute ΔAP", fontsize=8)
ax.set_title("Restatement\nnegative / null", fontsize=9)

# --- 2. survivor universe: composition, not performance --------------------
ax = axes[1]
ax.bar([0, 1], [100, 100], color="#DDDDDD", width=0.6)
ax.bar([0, 1], [64.4, 22.3], color="#1F6FB4", width=0.6)
ax.set_xticks([0, 1]); ax.set_xticklabels(["observations", "positive obs."], fontsize=7.4)
ax.set_ylabel("% retained", fontsize=8); ax.set_ylim(0, 128)
ax.set_title("Survivor universe\ncomposition shift", fontsize=9)
ax.text(0, 68, "−35.6%", ha="center", fontsize=7.6, fontweight="bold")
ax.text(1, 26, "−77.7%", ha="center", fontsize=7.6, fontweight="bold")
ax.text(0.5, 116, "prevalence\n0.00580 → 0.00201", ha="center", fontsize=6.4)

# --- 3. SIC vintage: exposure without positive-class reach -----------------
ax = axes[2]
ax.bar([0, 1], [4248, 2], color=["#1F6FB4", "#C1471B"], width=0.6)
ax.set_yscale("log"); ax.set_ylim(0.6, 60000)
ax.set_xticks([0, 1])
ax.set_xticklabels(["observations\naffected", "positive obs.\naffected"], fontsize=7.2)
ax.set_ylabel("count (log scale)", fontsize=8)
ax.set_title("SIC vintage\nno positive-class reach", fontsize=9)
ax.text(0, 7000, "4,248", ha="center", fontsize=7.6)
ax.text(1, 3.4, "2", ha="center", fontsize=7.6, fontweight="bold")
ax.text(0.5, 20000, "terminated before modelling", ha="center", fontsize=6.4)

# --- 4. temporal evaluation: heterogeneity, and what matching does ---------
ax = axes[3]
ax.bar([0, 1], [11.87, 0.04], color=["#999999", "#C1471B"], width=0.6)
ax.set_xticks([0, 1])
ax.set_xticklabels(["unmatched", "matched\ntraining volume"], fontsize=7.2)
ax.set_ylabel("cohort-median relative ΔAP (%)", fontsize=8)
ax.set_title("Temporal evaluation\nheterogeneous sensitivity", fontsize=9)
ax.text(0, 12.5, "+11.87%", ha="center", fontsize=7.6)
ax.text(1, 0.9, "+0.04%", ha="center", fontsize=7.6, fontweight="bold")
ax.set_ylim(0, 17.5)
ax.text(0.5, 15.4, "sign split 6+ / 5− / 1 zero", ha="center", fontsize=6.4)

fig.subplots_adjust(left=0.105, right=0.98, top=0.90, bottom=0.085,
                    wspace=0.34, hspace=0.42)
from _common import OUT
for ext in ("pdf", "png"):
    fig.savefig(OUT / f"fig5_contamination_channels.{ext}")
plt.close(fig)
print("wrote fig5_contamination_channels.pdf and fig5_contamination_channels.png")
