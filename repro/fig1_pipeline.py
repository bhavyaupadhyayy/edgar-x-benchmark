"""Figure 1: the point-in-time admissibility rule, and the pipeline that enforces it.

Panel (a) is a schematic of the rule, not a data plot. Panel (b) carries counts
read from the frozen release artifacts and the frozen result documents.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from _common import save

fig = plt.figure(figsize=(5.8, 5.9))
gs = fig.add_gridspec(2, 1, height_ratios=[0.86, 2.05], hspace=0.05)

# ---- (a) what the acceptance clock admits -------------------------------------
ax = fig.add_subplot(gs[0]); ax.set_xlim(0, 10); ax.set_ylim(0.05, 3.35); ax.axis("off")
ax.grid(False)
ax.add_patch(Rectangle((0.55, 0.62), 4.55, 2.30, facecolor="#EAF2F9",
                       edgecolor="none", zorder=0))
ax.add_patch(Rectangle((5.10, 0.62), 4.35, 2.30, facecolor="#F7F0EC",
                       edgecolor="none", zorder=0))
ax.annotate("", xy=(9.62, 0.62), xytext=(0.55, 0.62),
            arrowprops=dict(arrowstyle="-|>", linewidth=1.2, color="#333333"))
ax.plot([5.10, 5.10], [0.48, 2.92], color="#C1471B", linewidth=1.8, zorder=3)
ax.text(5.10, 3.08, "EDGAR acceptance timestamp $t$ of the 10-K",
        ha="center", fontsize=8.6, fontweight="bold", color="#C1471B")
ax.text(9.62, 0.30, "time", ha="right", fontsize=8)

ax.text(0.80, 2.62, "admissible at $t$", fontsize=8.2,
        fontweight="bold", color="#1F6FB4")
for j, s in enumerate(["facts from submissions accepted by $t$",
                       "the SIC code on the filing itself",
                       "the CIK printed on the document",
                       "Item 1A and Item 7 of this 10-K"]):
    ax.text(0.95, 2.26 - j * 0.38, f"• {s}", fontsize=7.1, va="center")

ax.text(5.34, 2.62, "inadmissible: known only later", fontsize=8.2,
        fontweight="bold", color="#C1471B")
for j, s in enumerate(["values restated in submissions after $t$",
                       "the registrant's present-day SIC code",
                       "a present-day filer universe",
                       "training rows from cohorts at or after $t$"]):
    ax.text(5.49, 2.26 - j * 0.38, f"• {s}", fontsize=7.1, va="center")
ax.set_title("(a) The acceptance clock defines the information set",
             fontsize=9.2, loc="left", pad=4)

# ---- (b) pipeline, read top to bottom -----------------------------------------
STAGES = [
    ("Acquisition",
     ["SEC bulk submissions archive", "52 DERA quarters (2012-2024)",
      "3,786 Item 1.03 8-K documents", "59,499 primary 10-K documents"]),
    ("Point-in-time reconstruction",
     ["acceptance timestamp as cutoff", "as-filed DERA facts only",
      "historical SIC, FIRE excluded", "CIK identity, PIT names"]),
    ("Event labelling",
     ["3,010 assembled events", "initial US Ch. 7/11 only",
      "actual petition date as event time", "365-day forward horizon"]),
    ("Contamination audit (4 channels)",
     ["restatement: negative / null", "survivor universe: composition shift",
      "SIC vintage: 2 positive obs. exposed", "random vs rolling: heterogeneous"]),
    ("Rolling benchmark",
     ["59,500 obs. / 437 positive obs.", "rolling-testable 54,351 / 408",
      "cohorts 2013-2024", "arms: ratios / text / combined"]),
]
bx = fig.add_subplot(gs[1])
bx.set_xlim(0, 10); bx.set_ylim(0, len(STAGES) * 2.02); bx.axis("off"); bx.grid(False)
for index, (title, bullets) in enumerate(STAGES):
    y = (len(STAGES) - 1 - index) * 2.02 + 0.30
    bx.add_patch(FancyBboxPatch((0.55, y), 8.9, 1.42,
                                boxstyle="round,pad=0.07,rounding_size=0.10",
                                linewidth=1.0, edgecolor="#333333",
                                facecolor="#F4F4F4"))
    bx.text(0.85, y + 1.17, title, fontsize=9.2, fontweight="bold", va="center")
    for j, b in enumerate(bullets):
        bx.text(0.95 + (j % 2) * 4.45, y + 0.74 - (j // 2) * 0.37, f"• {b}",
                fontsize=7.4, va="center")
    if index < len(STAGES) - 1:                      # arrows follow reading order
        bx.add_patch(FancyArrowPatch((5.0, y - 0.08), (5.0, y - 0.54),
                                     arrowstyle="-|>", mutation_scale=12,
                                     linewidth=1.1, color="#333333"))
bx.set_title("(b) Construction pipeline", fontsize=9.2, loc="left", pad=4)
save(fig, "fig1_pipeline")
