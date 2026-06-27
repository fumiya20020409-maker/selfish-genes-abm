# -*- coding: utf-8 -*-
"""
regen_fig1_fig5.py — 図1（ベースケース）と図5（スナップショット）だけ再生成
ラベルを英語表記にして文字化けを回避
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from run_analysis import (
    run_multi, mean_std_df, plot_mean_std, _snapshot_worker,
    N_STEPS, N_RUNS, BASE_SEED, FIGURES_DIR
)
from model import DEFAULT_PARAMS, SCENARIO_C_FIXED, SCENARIO_C_LOW, SCENARIO_C_HIGH

plt.rcParams.update({
    "font.size": 12, "axes.titlesize": 13, "axes.labelsize": 12,
    "legend.fontsize": 10, "figure.dpi": 150,
    "savefig.dpi": 300, "savefig.bbox": "tight",
})

print("Regenerating fig1 and fig5...")

# ── Fig 1: Baseline ──
print("[Fig1] Running baseline simulation (n=20)...")
dfs_base = run_multi(DEFAULT_PARAMS)

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

ax = axes[0]
mean_cr, std_cr = mean_std_df(dfs_base, "CoopRatio")
plot_mean_std(ax, mean_cr, std_cr, "#3498db", f"Cooperation rate (mean+/-SD, n={N_RUNS})")
ax.axhline(0.5, color="gray", linestyle="--", linewidth=1.0, alpha=0.6, label="50% line")
ax.set_xlabel("Step"); ax.set_ylabel("Cooperation rate"); ax.set_ylim(0, 1)
ax.set_title("(a) Cooperation rate over time"); ax.legend(); ax.grid(True, alpha=0.3)

ax2 = axes[1]
mean_coop,  std_coop   = mean_std_df(dfs_base, "Cooperators")
mean_defect, std_defect = mean_std_df(dfs_base, "Defectors")
x = range(len(mean_coop))
ax2.plot(x, mean_coop,   color="#3498db", linewidth=1.5, label="Cooperators")
ax2.plot(x, mean_defect, color="#e74c3c", linewidth=1.5, label="Defectors")
ax2.fill_between(x, mean_coop - std_coop,   mean_coop + std_coop,   color="#3498db", alpha=0.15)
ax2.fill_between(x, mean_defect - std_defect, mean_defect + std_defect, color="#e74c3c", alpha=0.15)
ax2.set_xlabel("Step"); ax2.set_ylabel("Population")
ax2.set_title("(b) Population by strategy"); ax2.legend(loc="upper left"); ax2.grid(True, alpha=0.3)

fig.suptitle(f"Fig.1: Baseline (d=0.1, m=0.01, n={N_RUNS} runs)", fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "fig1_baseline.png"))
plt.close()
print("  -> fig1_baseline.png saved")

# ── Fig 5: Spatial snapshots ──
print("[Fig5] Running snapshot simulations (3 conditions)...")
CHECKPOINTS   = [100, 250, N_STEPS]
snapshot_keys = ["Fixed d=0.0", "Low d=0.1", "High d=0.9"]
snapshot_cfgs = [SCENARIO_C_FIXED, SCENARIO_C_LOW, SCENARIO_C_HIGH]
snap_results  = [_snapshot_worker({**p, "seed": BASE_SEED}, CHECKPOINTS, N_STEPS)
                 for p in snapshot_cfgs]

cmap = mcolors.ListedColormap(["#f0f0f0", "#3498db", "#e74c3c"])
fig, axes = plt.subplots(3, 3, figsize=(15, 15))

for row, (label, (snaps, ratios)) in enumerate(zip(snapshot_keys, snap_results)):
    for col, (cp, snap, ratio) in enumerate(zip(CHECKPOINTS, snaps, ratios)):
        ax = axes[row][col]
        if snap is not None:
            ax.imshow(snap.T, cmap=cmap, vmin=0, vmax=2, origin="lower")
        else:
            ax.set_facecolor("#f0f0f0")
        if col == 0:
            ax.set_ylabel(label, fontsize=11, fontweight="bold")
        if row == 0:
            ax.set_title(f"step {cp}", fontsize=11)
        ax.text(0.97, 0.03, f"C={ratio:.1%}",
                transform=ax.transAxes, fontsize=8,
                ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))
        ax.set_xticks([]); ax.set_yticks([])

legend_elements = [
    Patch(facecolor="#3498db", label="Cooperators"),
    Patch(facecolor="#e74c3c", label="Defectors"),
    Patch(facecolor="#f0f0f0", label="Empty"),
]
fig.legend(handles=legend_elements, loc="lower center",
           ncol=3, bbox_to_anchor=(0.5, 0.01), fontsize=11)
fig.suptitle("Fig.5: Scenario C - Spatial distribution by mobility\n(rows: mobility; cols: time step)", fontsize=13)
plt.tight_layout(rect=[0, 0.05, 1, 1])
plt.savefig(os.path.join(FIGURES_DIR, "fig5_snapshots.png"), bbox_inches="tight")
plt.close()
print("  -> fig5_snapshots.png saved")

print("\nDone")
