"""Figure 4: performance at fixed analyst-review budgets.

Ranking results under a fixed review capacity. NOT a deployment claim: no
threshold, operating point or cost model is proposed.

Lift@k is precision@k divided by cohort prevalence and is therefore proportional
to the precision panel; it is reported in Table 5 rather than plotted again.
"""
import matplotlib.pyplot as plt
import numpy as np
from _common import ARMS, COLOURS, LABELS, cohorts, save

rows = cohorts("B")
w = np.array([int(r["positives"]) for r in rows], float); w /= w.sum()
BUDGETS = ["25", "50", "100", "250", "top1pct"]
SHOWN = ["25", "50", "100", "250", "top 1%"]

def ew(metric, arm):
    return [float(np.dot(w, [float(r[f"{metric}@{b}_{arm}"]) for r in rows]))
            for b in BUDGETS]

fig, axes = plt.subplots(1, 2, figsize=(5.8, 2.7))
x = np.arange(len(BUDGETS)); width = 0.26
for ax, metric, title in zip(axes, ("precision", "recall"),
                             ("Precision@k", "Recall@k")):
    for i, arm in enumerate(ARMS):
        ax.bar(x + (i - 1) * width, ew(metric, arm), width,
               color=COLOURS[arm], label=LABELS[arm])
    ax.set_xticks(x); ax.set_xticklabels(SHOWN, fontsize=7.4)
    ax.set_title(title, fontsize=9.5)
    ax.set_xlabel("review budget", fontsize=8)
axes[0].set_ylabel("event-weighted value")
axes[0].legend(frameon=False, fontsize=7.2, loc="upper right")
save(fig, "fig4_review_budget")
