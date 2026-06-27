"""
regenerate_figures.py — summary_results.csv から図2〜4・6を高速再生成
（run_analysis.py のシミュレーション部分をスキップし、図だけ再描画する）
図1・5 はシミュレーション実行が必要なため対象外。
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Meiryo"
import matplotlib.pyplot as plt
plt.rcParams.update({
    "font.size": 12, "axes.titlesize": 13, "axes.labelsize": 12,
    "legend.fontsize": 10, "figure.dpi": 150,
    "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.family": "Meiryo",
})

import numpy as np
import pandas as pd

BASE_DIR  = os.path.dirname(os.path.dirname(__file__))
FIGS_DIR  = os.path.join(BASE_DIR, "data", "figures")
CSV_PATH  = os.path.join(BASE_DIR, "data", "summary_results.csv")
SENS_PATH = os.path.join(BASE_DIR, "data", "sensitivity_results.csv")
os.makedirs(FIGS_DIR, exist_ok=True)

df = pd.read_csv(CSV_PATH)

def ci(mean, std, n=20):
    return 1.96 * std / np.sqrt(n)

# ── 図2：シナリオA ──────────────────────────────────────────
print("[図2] シナリオA...")
rates  = [0.2, 0.5, 1.0, 2.0, 3.0, 5.0]
a_rows = [df[df["scenario"] == f"A_rate{r}"].iloc[0] for r in rates]
means  = [r["final_coop_ratio_mean"] for r in a_rows]
stds   = [r["final_coop_ratio_std"]  for r in a_rows]
cis    = [ci(m, s) for m, s in zip(means, stds)]

colors_a = plt.cm.Blues(np.linspace(0.3, 0.9, len(rates)))
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
ax = axes[0]
for i, (r, m, s) in enumerate(zip(rates, means, stds)):
    ax.errorbar([r], [m], yerr=[s], fmt="o-", color=colors_a[i],
                capsize=5, linewidth=1.5, label=f"$R_e$={r}")
ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
ax.set_xlabel("基礎回復率 $R_e$"); ax.set_ylabel("最終協力率"); ax.set_ylim(0, 1)
ax.set_title("(a) $R_e$ 別の最終協力率（mean±SD）"); ax.legend(fontsize=9); ax.grid(True, alpha=0.3)

ax2 = axes[1]
bars = ax2.bar([str(r) for r in rates], means, yerr=cis, capsize=4,
               color=colors_a, edgecolor="black", linewidth=0.5)
ax2.axhline(0.5, color="red", linestyle="--", linewidth=1.0, alpha=0.7, label="50%ライン")
ax2.set_xlabel("基礎回復率 $R_e$（$b_c=0.5$ 固定）"); ax2.set_ylabel("最終協力率"); ax2.set_ylim(0, 1)
ax2.set_title("(b) $R_e$ 別の最終協力率比較（mean±95%CI）"); ax2.legend(); ax2.grid(True, alpha=0.3, axis="y")
for bar, val in zip(bars, means):
    ax2.text(bar.get_x() + bar.get_width()/2, val + 0.05,
             f"{val:.3f}", ha="center", va="bottom", fontsize=9)
fig.suptitle("図2：シナリオA — リソース量と協力率の関係 (n=20)", fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(FIGS_DIR, "fig2_scenario_a.png"))
plt.close()
print("  -> fig2_scenario_a.png 保存完了")

# ── 図3：シナリオB ──────────────────────────────────────────
print("[図3] シナリオB...")
b_keys   = ["e=0.0 (完全認識)", "e=0.05", "e=0.10", "e=0.20", "緑ひげなし"]
b_labels = ["ε=0.0（完全認識）", "ε=0.05", "ε=0.10", "ε=0.20", "緑ひげなし"]
b_rows   = [df[df["scenario"] == k].iloc[0] for k in b_keys]
means_b  = [r["final_coop_ratio_mean"] for r in b_rows]
stds_b   = [r["final_coop_ratio_std"]  for r in b_rows]
cis_b    = [ci(m, s) for m, s in zip(means_b, stds_b)]
colors_b = ["#1a237e","#3949ab","#7986cb","#c5cae9","#e53935"]

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
ax = axes[0]
eps_vals = [0.0, 0.05, 0.10, 0.20, None]
for label, m, s, color in zip(b_labels, means_b, stds_b, colors_b):
    ax.bar([label], [m], yerr=[s], capsize=4, color=color,
           edgecolor="black", linewidth=0.5, label=label)
ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
ax.set_ylabel("最終協力率"); ax.set_ylim(0, 1)
ax.set_title("(a) 条件別の最終協力率（mean±SD）")
ax.tick_params(axis="x", labelsize=9); ax.grid(True, alpha=0.3, axis="y")

ax2 = axes[1]
bars = ax2.barh(b_labels, means_b, xerr=cis_b, capsize=4,
                color=colors_b, edgecolor="black", linewidth=0.5)
ax2.axvline(0.5, color="red", linestyle="--", linewidth=1.0, alpha=0.7)
ax2.set_xlabel("最終協力率"); ax2.set_xlim(0, 1)
ax2.set_title("(b) 条件別の最終協力率比較（mean±95%CI）")
ax2.grid(True, alpha=0.3, axis="x")
for bar, val in zip(bars, means_b):
    ax2.text(val + 0.02, bar.get_y() + bar.get_height()/2,
             f"{val:.3f}", va="center", fontsize=9)
fig.suptitle("図3：シナリオB — 緑ひげ効果と認識誤り率ε (n=20)", fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(FIGS_DIR, "fig3_scenario_b.png"))
plt.close()
print("  -> fig3_scenario_b.png 保存完了")

# ── 図4：シナリオC ──────────────────────────────────────────
print("[図4] シナリオC...")
c_keys   = ["固定 d=0.0", "低移動 d=0.1", "中移動 d=0.3", "高移動 d=0.9"]
c_labels = ["$d=0.0$（固定）", "$d=0.1$（低）", "$d=0.3$（中）", "$d=0.9$（高）"]
d_vals   = [0.0, 0.1, 0.3, 0.9]
c_rows   = [df[df["scenario"] == k].iloc[0] for k in c_keys]
means_c  = [r["final_coop_ratio_mean"] for r in c_rows]
stds_c   = [r["final_coop_ratio_std"]  for r in c_rows]
cis_c    = [ci(m, s) for m, s in zip(means_c, stds_c)]
colors_c = ["#1b5e20","#388e3c","#81c784","#c8e6c9"]

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
ax = axes[0]
for label, m, s, color in zip(c_labels, means_c, stds_c, colors_c):
    ax.bar([label], [m], yerr=[s], capsize=4, color=color,
           edgecolor="black", linewidth=0.5)
ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
ax.set_ylabel("最終協力率"); ax.set_ylim(0, 1)
ax.set_title("(a) 移動確率別の最終協力率（mean±SD）")
ax.grid(True, alpha=0.3, axis="y")

ax2 = axes[1]
ax2.errorbar(d_vals, means_c, yerr=cis_c,
             fmt="o-", color="#2e7d32", linewidth=2, markersize=8, capsize=5)
ax2.axhline(0.5, color="red", linestyle="--", linewidth=1.0, alpha=0.7)
ax2.set_xlabel("移動確率 $d$"); ax2.set_ylabel("最終協力率"); ax2.set_ylim(0, 1)
ax2.set_title("(b) 移動確率 $d$ と最終協力率（mean±95%CI）")
ax2.grid(True, alpha=0.3)
for x, y in zip(d_vals, means_c):
    ax2.annotate(f"{y:.3f}", (x, y), textcoords="offset points", xytext=(5, 5), fontsize=9)
fig.suptitle("図4：シナリオC — 移動性と協力率の関係 (n=20)", fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(FIGS_DIR, "fig4_scenario_c.png"))
plt.close()
print("  -> fig4_scenario_c.png 保存完了")

# ── 図6：感度分析 ──────────────────────────────────────────
print("[図6] 感度分析...")
sens = pd.read_csv(SENS_PATH)
params = sens["parameter"].unique()
fig, axes = plt.subplots(1, len(params), figsize=(5 * len(params), 4))
for ax, param in zip(axes, params):
    sub = sens[sens["parameter"] == param]
    ax.errorbar(sub["value"], sub["mean_coop_ratio"], yerr=sub["std_coop_ratio"],
                fmt="o-", capsize=5, linewidth=2, markersize=7, color="#3b5998")
    ax.axhline(0.5, color="red", linestyle=":", linewidth=0.8, alpha=0.6)
    param_labels = {"mutation_rate": "突然変異率 $m$",
                    "max_age": "最大寿命 $A_{\\mathrm{max}}$",
                    "reproduce_threshold": "繁殖閾値 $E_{\\mathrm{rep}}$"}
    ax.set_xlabel(param_labels.get(param, param), fontsize=11)
    ax.set_ylabel("最終協力率", fontsize=11)
    ax.set_ylim(0, 1)
    ax.set_title(f"{param_labels.get(param, param)}\n感度分析 (n=10)", fontsize=11)
    ax.grid(True, alpha=0.3)
fig.suptitle("図6：パラメータ感度分析", fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(FIGS_DIR, "fig6_sensitivity.png"))
plt.close()
print("  -> fig6_sensitivity.png 保存完了")

print("\n全図の再生成完了")
