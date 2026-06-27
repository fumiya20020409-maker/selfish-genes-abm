"""
run_analysis.py — 論文用グラフを全て生成するスクリプト
実行方法：
    cd selfish_genes
    python run_analysis.py

注意：Windows では multiprocessing.Pool がプロセスを大量生成して固まるため、
  逐次実行に変更済み。N_RUNS 回異なるシードで実行し平均±標準偏差を描画する。
  ThreadPoolExecutor はGILの影響で速度改善がなかったため採用しない。
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import matplotlib
matplotlib.use("Agg")  # ディスプレイなしで実行
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from model import (
    SelfishGeneModel,
    DEFAULT_PARAMS,
    SCENARIO_A_BONUS_HIGH, SCENARIO_A_BONUS_LOW,
    SCENARIO_B_PERFECT, SCENARIO_B_ERROR05, SCENARIO_B_ERROR10,
    SCENARIO_B_ERROR20, SCENARIO_B_NONE,
    SCENARIO_C_FIXED, SCENARIO_C_LOW, SCENARIO_C_MID, SCENARIO_C_HIGH,
)

# --------------------------------------------------------------------------
# 設定
# --------------------------------------------------------------------------
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "data", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

plt.rcParams.update({
    "font.size": 12,
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

# N_STEPS 設定根拠（指摘⑥への対応）：
#   予備実験では協力率の変動幅が step~150 以降で ±0.02 以内に収束することを確認。
#   500ステップはその3倍以上のバッファを持つ設定であり、収束の安全余裕として妥当。
#   加えて run_simulation() 内に早期終了条件（収束判定 + 全滅検出）を実装している。
N_STEPS = 500

# N_RUNS 設定根拠（指摘②への対応）：
#   Lorscheid et al. (2012) が推奨する最低20回以上の反復実行を満たす。
#   1シナリオ×1試行≈1.2秒 → 16シナリオ×20試行=320回 ≈ 6〜7分（許容範囲）
N_RUNS  = 20    # 各シナリオを異なるシードで繰り返す回数（平均±SD 算出用）

# 再現性のため固定シードを使用（論文付録A記載値と一致）
# N_RUNS 回の試行は BASE_SEED, BASE_SEED+1, ... BASE_SEED+(N_RUNS-1) を使用
BASE_SEED = 42


# --------------------------------------------------------------------------
# シミュレーション実行ユーティリティ
# --------------------------------------------------------------------------

_CONVERGE_WINDOW    = 20    # 収束判定に使う直近ステップ数
_CONVERGE_THRESHOLD = 0.01  # 収束判定の協力率変動閾値（±1%以内で収束とみなす）

def run_simulation(params: dict, n_steps: int = N_STEPS) -> pd.DataFrame:
    """
    1回のシミュレーションを実行して DataCollector の DataFrame を返す。

    早期終了条件（指摘⑥への対応）：
        1. 全エージェントが死滅した場合
        2. 直近 _CONVERGE_WINDOW ステップの協力率変動が _CONVERGE_THRESHOLD 以下の場合
           （協力率が安定的に収束したと判断）
    """
    model = SelfishGeneModel(**params)
    recent_coop: list[float] = []

    for step in range(n_steps):
        model.step()
        if len(model.agents) == 0:
            break
        # 収束判定：直近ウィンドウ内の変動を確認
        recent_coop.append(model._coop_ratio())
        if len(recent_coop) > _CONVERGE_WINDOW:
            recent_coop.pop(0)
        if (len(recent_coop) == _CONVERGE_WINDOW
                and (max(recent_coop) - min(recent_coop)) <= _CONVERGE_THRESHOLD):
            break  # 収束とみなして早期終了

    return model.datacollector.get_model_vars_dataframe()


def run_multi(params: dict, n_steps: int = N_STEPS, n_runs: int = N_RUNS) -> list[pd.DataFrame]:
    """
    同一パラメータを n_runs 回、異なるシードで実行して DataFrame のリストを返す。
    シードは BASE_SEED, BASE_SEED+1, ... BASE_SEED+(n_runs-1) を使用する。
    """
    results = []
    for i in range(n_runs):
        seeded = {**params, "seed": (BASE_SEED + i) % 2**31}
        results.append(run_simulation(seeded, n_steps))
    return results


def mean_std_df(dfs: list[pd.DataFrame], col: str) -> tuple[pd.Series, pd.Series]:
    """
    複数 DataFrame の同一列について、ステップ軸を揃えた平均と標準偏差を返す。
    実行により長さが異なる場合は最短に揃える（NaN 伝搬を防ぐ）。
    """
    min_len = min(len(df) for df in dfs)
    mat = np.array([df[col].values[:min_len] for df in dfs])
    return pd.Series(mat.mean(axis=0)), pd.Series(mat.std(axis=0))


def plot_mean_std(ax, mean: pd.Series, std: pd.Series, color: str,
                  label: str, linewidth: float = 1.8, linestyle: str = "-") -> None:
    """平均線 + ±1SD の塗り潰しを描画するヘルパー。"""
    x = range(len(mean))
    ax.plot(x, mean, color=color, linewidth=linewidth,
            linestyle=linestyle, label=label)
    ax.fill_between(x, mean - std, mean + std, color=color, alpha=0.15)


def _snapshot_worker(params, checkpoints, n_steps):
    """
    図5用。checkpoints の各ステップ時点のスナップショットと協力率を返す。
    戻り値: (snapshots, coop_ratios)
      snapshots   : [snap_step1, snap_step2, ...]  各 np.ndarray (50×50)
      coop_ratios : [ratio_step1, ratio_step2, ...]
    """
    model = SelfishGeneModel(**params)
    checkpoints_set = set(checkpoints)
    snapshots, coop_ratios = {}, {}
    for step in range(1, n_steps + 1):
        model.step()
        if len(model.agents) == 0:
            break
        if step in checkpoints_set:
            snapshots[step]   = model.get_grid_snapshot()
            coop_ratios[step] = model._coop_ratio()
    return ([snapshots.get(c)   for c in checkpoints],
            [coop_ratios.get(c, 0.0) for c in checkpoints])


def run_sequential(param_list: list, n_steps: int = N_STEPS) -> list:
    """シナリオリストを逐次実行して DataFrame のリストを返す。（後方互換）"""
    return [run_simulation(p, n_steps) for p in param_list]


# --------------------------------------------------------------------------
# メイン処理（Windows の multiprocessing ガードが必須）
# --------------------------------------------------------------------------

def main():
    resource_rates  = [0.2, 0.5, 1.0, 2.0, 3.0, 5.0]
    scenario_b_keys = ["e=0.0 (完全認識)", "e=0.05", "e=0.10", "e=0.20", "緑ひげなし"]
    scenario_b_cfgs = [SCENARIO_B_PERFECT, SCENARIO_B_ERROR05, SCENARIO_B_ERROR10,
                       SCENARIO_B_ERROR20, SCENARIO_B_NONE]
    scenario_c_keys = ["固定 d=0.0", "低移動 d=0.1", "中移動 d=0.3", "高移動 d=0.9"]
    scenario_c_cfgs = [SCENARIO_C_FIXED, SCENARIO_C_LOW, SCENARIO_C_MID, SCENARIO_C_HIGH]
    snapshot_keys   = ["固定 d=0.0", "低移動 d=0.1", "高移動 d=0.9"]
    snapshot_cfgs   = [SCENARIO_C_FIXED, SCENARIO_C_LOW, SCENARIO_C_HIGH]

    # ------------------------------------------------------------------
    # 全シナリオを N_RUNS 回ずつ逐次実行
    # シナリオ数 = 1(base) + 6(A) + 5(B) + 4(C) = 16
    # 各シナリオにつき BASE_SEED+0, +1, ... +N_RUNS-1 のシードを使用
    # ------------------------------------------------------------------
    all_base_params = (
        [DEFAULT_PARAMS] +
        [{**DEFAULT_PARAMS, "resource_recovery_rate": rr} for rr in resource_rates] +
        scenario_b_cfgs +
        scenario_c_cfgs
    )
    total_runs = len(all_base_params) * N_RUNS
    print(f"全 {len(all_base_params)} シナリオ × {N_RUNS} 回 = {total_runs} 回を逐次実行中...")
    print(f"  BASE_SEED={BASE_SEED}, N_STEPS={N_STEPS}\n")

    # シナリオ × Run の2次元リストで結果を保持
    # multi_results[scenario_idx][run_idx] = DataFrame
    multi_results = [run_multi(p) for p in all_base_params]
    print("完了\n")

    # 結果を名前付きに分割（各エントリは list[DataFrame]）
    idx = 0
    dfs_base = multi_results[idx]; idx += 1
    results_a = {rr: multi_results[idx + i] for i, rr in enumerate(resource_rates)}
    idx += len(resource_rates)
    results_b = {k: multi_results[idx + i] for i, k in enumerate(scenario_b_keys)}
    idx += len(scenario_b_keys)
    results_c = {k: multi_results[idx + i] for i, k in enumerate(scenario_c_keys)}

    # 各シナリオの平均最終協力率をログ出力（最後のステップの平均）
    def mean_final(dfs, col="CoopRatio"):
        return np.mean([df[col].iloc[-1] for df in dfs])

    print(f"  baseline    最終協力率(mean): {mean_final(dfs_base):.3f}"
          f"  個体数(mean): {np.mean([df['TotalAgents'].iloc[-1] for df in dfs_base]):.0f}")
    for rr in resource_rates:
        print(f"  A rate={rr}  -> {mean_final(results_a[rr]):.3f}")
    for k in scenario_b_keys:
        print(f"  B {k}  -> {mean_final(results_b[k]):.3f}")
    for k in scenario_c_keys:
        print(f"  C {k}  -> {mean_final(results_c[k]):.3f}")

    # ------------------------------------------------------------------
    # 図5用：3条件 × 3時点のスナップショット（代表シード1回のみ）
    # ------------------------------------------------------------------
    CHECKPOINTS = [100, 250, N_STEPS]
    print(f"\n図5用スナップショット取得中（3シナリオ × {CHECKPOINTS} ステップ）...")
    snap_results = [_snapshot_worker({**p, "seed": BASE_SEED}, CHECKPOINTS, N_STEPS)
                    for p in snapshot_cfgs]
    print("完了\n")

    # ==================================================================
    # 図1：ベースケース（平均±SD）
    # ==================================================================
    print("[1/5] 図1：ベースケース描画中...")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    ax = axes[0]
    mean_cr, std_cr = mean_std_df(dfs_base, "CoopRatio")
    plot_mean_std(ax, mean_cr, std_cr, "#3498db", f"協力率 (mean±SD, n={N_RUNS})")
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1.0, alpha=0.6, label="50%ライン")
    ax.set_xlabel("ステップ"); ax.set_ylabel("協力率"); ax.set_ylim(0, 1)
    ax.set_title("(a) 協力率の時系列推移"); ax.legend(); ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    mean_coop, std_coop   = mean_std_df(dfs_base, "Cooperators")
    mean_defect, std_defect = mean_std_df(dfs_base, "Defectors")
    x = range(len(mean_coop))
    ax2.plot(x, mean_coop,   color="#3498db", linewidth=1.5, label="協力者")
    ax2.plot(x, mean_defect, color="#e74c3c", linewidth=1.5, label="裏切り者")
    ax2.fill_between(x, mean_coop - std_coop,   mean_coop + std_coop,   color="#3498db", alpha=0.15)
    ax2.fill_between(x, mean_defect - std_defect, mean_defect + std_defect, color="#e74c3c", alpha=0.15)
    ax2.set_xlabel("ステップ"); ax2.set_ylabel("個体数")
    ax2.set_title("(b) 戦略別個体数の推移"); ax2.legend(loc="upper left"); ax2.grid(True, alpha=0.3)

    fig.suptitle(f"図1：ベースケース (diffusion_rate=0.1, mutation_rate=0.01, n={N_RUNS} runs)", fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig1_baseline.png"))
    plt.close()
    print("      -> fig1_baseline.png 保存完了")

    # ==================================================================
    # 図2：シナリオA — リソース量別（平均±SD）
    # ==================================================================
    print("[2/5] 図2：シナリオA描画中...")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    colors_a = plt.cm.Blues(np.linspace(0.3, 0.9, len(resource_rates)))

    ax = axes[0]
    for i, rr in enumerate(resource_rates):
        m, s = mean_std_df(results_a[rr], "CoopRatio")
        plot_mean_std(ax, m, s, colors_a[i], f"rate={rr}", linewidth=1.5)
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("ステップ"); ax.set_ylabel("協力率"); ax.set_ylim(0, 1)
    ax.set_title("(a) リソース量別の協力率推移"); ax.legend(fontsize=9); ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    final_means = [np.mean([df["CoopRatio"].iloc[-1] for df in results_a[rr]]) for rr in resource_rates]
    final_stds  = [np.std( [df["CoopRatio"].iloc[-1] for df in results_a[rr]]) for rr in resource_rates]
    bars = ax2.bar([str(rr) for rr in resource_rates], final_means,
                   yerr=final_stds, capsize=4,
                   color=colors_a, edgecolor="black", linewidth=0.5)
    ax2.axhline(0.5, color="red", linestyle="--", linewidth=1.0, alpha=0.7, label="50%ライン")
    ax2.set_xlabel("resource_recovery_rate\n(coop_bonus_rate は固定=0.5)"); ax2.set_ylabel("最終協力率"); ax2.set_ylim(0, 1)
    ax2.set_title("(b) リソース量別の最終協力率 (mean±SD)"); ax2.legend(); ax2.grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars, final_means):
        ax2.text(bar.get_x() + bar.get_width() / 2, val + 0.05,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=9)

    fig.suptitle(f"図2：シナリオA — リソース量と協力率の関係 (n={N_RUNS} runs)", fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig2_scenario_a.png"))
    plt.close()
    print("      -> fig2_scenario_a.png 保存完了")

    # ==================================================================
    # 図3：シナリオB — 緑ひげ効果・認識誤り率（平均±SD）
    # ==================================================================
    print("[3/5] 図3：シナリオB描画中...")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    colors_b = ["#1a237e", "#3949ab", "#7986cb", "#c5cae9", "#e53935"]

    ax = axes[0]
    for (label, dfs), color in zip(results_b.items(), colors_b):
        m, s = mean_std_df(dfs, "CoopRatio")
        plot_mean_std(ax, m, s, color, label, linewidth=1.5,
                      linestyle="--" if label == "緑ひげなし" else "-")
    ax.axhline(0.5, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("ステップ"); ax.set_ylabel("協力率"); ax.set_ylim(0, 1)
    ax.set_title("(a) 認識誤り率別の協力率推移"); ax.legend(fontsize=9); ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    labels_b   = list(results_b.keys())
    finals_b_m = [np.mean([df["CoopRatio"].iloc[-1] for df in results_b[l]]) for l in labels_b]
    finals_b_s = [np.std( [df["CoopRatio"].iloc[-1] for df in results_b[l]]) for l in labels_b]
    bars = ax2.barh(labels_b, finals_b_m, xerr=finals_b_s, capsize=4,
                    color=colors_b, edgecolor="black", linewidth=0.5)
    ax2.axvline(0.5, color="red", linestyle="--", linewidth=1.0, alpha=0.7)
    ax2.set_xlabel("最終協力率"); ax2.set_xlim(0, 1)
    ax2.set_title("(b) 条件別の最終協力率 (mean±SD)"); ax2.grid(True, alpha=0.3, axis="x")
    for bar, val in zip(bars, finals_b_m):
        ax2.text(val + 0.04, bar.get_y() + bar.get_height() / 2,
                 f"{val:.2f}", va="center", fontsize=9)

    fig.suptitle(f"図3：シナリオB — 緑ひげ効果と認識誤り率εの影響 (n={N_RUNS} runs)", fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig3_scenario_b.png"))
    plt.close()
    print("      -> fig3_scenario_b.png 保存完了")

    # ==================================================================
    # 図4：シナリオC — 移動性（平均±SD）
    # ==================================================================
    print("[4/5] 図4：シナリオC描画中...")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    colors_c = ["#1b5e20", "#388e3c", "#81c784", "#c8e6c9"]

    ax = axes[0]
    for (label, dfs), color in zip(results_c.items(), colors_c):
        m, s = mean_std_df(dfs, "CoopRatio")
        plot_mean_std(ax, m, s, color, label, linewidth=1.8)
    ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("ステップ"); ax.set_ylabel("協力率"); ax.set_ylim(0, 1)
    ax.set_title("(a) 移動性別の協力率推移"); ax.legend(); ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    d_values   = [0.0, 0.1, 0.3, 0.9]
    finals_c_m = [np.mean([df["CoopRatio"].iloc[-1] for df in results_c[l]]) for l in results_c.keys()]
    finals_c_s = [np.std( [df["CoopRatio"].iloc[-1] for df in results_c[l]]) for l in results_c.keys()]
    ax2.errorbar(d_values, finals_c_m, yerr=finals_c_s,
                 fmt="o-", color="#2e7d32", linewidth=2, markersize=8, capsize=5)
    ax2.axhline(0.5, color="red", linestyle="--", linewidth=1.0, alpha=0.7)
    ax2.set_xlabel("diffusion_rate (移動性)"); ax2.set_ylabel("最終協力率"); ax2.set_ylim(0, 1)
    ax2.set_title("(b) 移動性と最終協力率の関係 (mean±SD)"); ax2.grid(True, alpha=0.3)
    for x, y in zip(d_values, finals_c_m):
        ax2.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(5, 5), fontsize=9)

    fig.suptitle(f"図4：シナリオC — 移動性（diffusion_rate）と協力率の関係 (n={N_RUNS} runs)", fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "fig4_scenario_c.png"))
    plt.close()
    print("      -> fig4_scenario_c.png 保存完了")

    # ==================================================================
    # 図5：空間スナップショット（3条件 × 3時点 の 3×3 グリッド）
    #   行 = 条件（d=0.0 / d=0.1 / d=0.9）
    #   列 = 時点（100 / 250 / 500 ステップ）
    #   代表シード（BASE_SEED）による1回の実行から取得
    # ==================================================================
    print("[5/5] 図5：空間スナップショット描画中...")
    cmap = mcolors.ListedColormap(["#f0f0f0", "#3498db", "#e74c3c"])
    n_rows, n_cols = len(snapshot_keys), len(CHECKPOINTS)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 5 * n_rows))

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
            print(f"      {label} step={cp} -> {ratio:.3f}")

    legend_elements = [
        Patch(facecolor="#3498db", label="協力者"),
        Patch(facecolor="#e74c3c", label="裏切り者"),
        Patch(facecolor="#f0f0f0", label="空"),
    ]
    fig.legend(handles=legend_elements, loc="lower center",
               ncol=3, bbox_to_anchor=(0.5, 0.01), fontsize=11)
    fig.suptitle("図5：シナリオC — 移動性別・時系列空間分布\n"
                 "（行：移動性条件　列：ステップ数）", fontsize=13)
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(os.path.join(FIGURES_DIR, "fig5_snapshots.png"), bbox_inches="tight")
    plt.close()
    print("      -> fig5_snapshots.png 保存完了")

    # ==================================================================
    # サマリーCSV（mean / std / n_runs を記録）
    # ==================================================================
    def scenario_stats(dfs, col="CoopRatio"):
        finals = [df[col].iloc[-1] for df in dfs]
        return np.mean(finals), np.std(finals)

    rows = []
    rows.append(("baseline", *scenario_stats(dfs_base)))
    for rr in resource_rates:
        rows.append((f"A_rate{rr}", *scenario_stats(results_a[rr])))
    for k in scenario_b_keys:
        rows.append((k, *scenario_stats(results_b[k])))
    for k in scenario_c_keys:
        rows.append((k, *scenario_stats(results_c[k])))

    summary = pd.DataFrame(rows, columns=["scenario", "final_coop_ratio_mean", "final_coop_ratio_std"])
    summary["n_runs"]    = N_RUNS
    summary["n_steps"]   = N_STEPS
    summary["base_seed"] = BASE_SEED
    csv_path = os.path.join(os.path.dirname(__file__), "data", "summary_results.csv")
    summary.to_csv(csv_path, index=False)

    print()
    print("=" * 60)
    print("全グラフ生成完了！")
    print(f"出力先: {FIGURES_DIR}")
    print(f"設定  : N_STEPS={N_STEPS}, N_RUNS={N_RUNS}, BASE_SEED={BASE_SEED}")
    print("=" * 60)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
