"""
batch_run.py — パラメータ感度分析スクリプト（指摘⑧への対応）

論文 §4.5「パラメータ感度分析」に対応。
mutation_rate / max_age / reproduce_threshold の3パラメータについて、
値を変えた場合の最終協力率への影響を測定し CSV + グラフで出力する。

実行方法：
    cd selfish_genes
    python batch_run.py

実行時間目安（N_RUNS=10、逐次実行）：
    - 3パラメータ × 5水準 × 10試行 = 150回 ≈ 3〜4分
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Meiryo"
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from model import SelfishGeneModel, DEFAULT_PARAMS

# --------------------------------------------------------------------------
# 設定
# --------------------------------------------------------------------------
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "data", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

N_STEPS     = 500
N_RUNS      = 10   # 感度分析は10試行で充分（精度と時間のバランス）
BASE_SEED   = 42

# 感度分析対象パラメータとスウィープ範囲（指摘⑧への直接対応）
SENSITIVITY_PARAMS = {
    "mutation_rate": [0.001, 0.005, 0.01, 0.05, 0.10],
    "max_age":       [20, 30, 50, 70, 100],
    "reproduce_threshold": [10.0, 12.0, 15.0, 18.0, 22.0],
}

# 収束判定（run_analysis.py と同じ基準）
_CONVERGE_WINDOW    = 20
_CONVERGE_THRESHOLD = 0.01


# --------------------------------------------------------------------------
# ユーティリティ
# --------------------------------------------------------------------------

def run_simulation_batch(params: dict) -> float:
    """
    1回のシミュレーションを実行し、最終ステップの協力率を返す。
    早期終了（収束 / 全滅）に対応。
    """
    model = SelfishGeneModel(**params)
    recent_coop: list[float] = []

    for _ in range(N_STEPS):
        model.step()
        if len(model.agents) == 0:
            return 0.0
        recent_coop.append(model._coop_ratio())
        if len(recent_coop) > _CONVERGE_WINDOW:
            recent_coop.pop(0)
        if (len(recent_coop) == _CONVERGE_WINDOW
                and (max(recent_coop) - min(recent_coop)) <= _CONVERGE_THRESHOLD):
            break

    return model._coop_ratio()


def sweep_param(param_name: str, values: list) -> tuple[list, list]:
    """
    1つのパラメータをスウィープし、各値での平均・標準偏差を返す。
    他のパラメータは DEFAULT_PARAMS で固定。
    """
    means, stds = [], []
    for val in values:
        ratios = []
        for i in range(N_RUNS):
            params = {**DEFAULT_PARAMS, param_name: val,
                      "seed": (BASE_SEED + i) % 2**31}
            ratios.append(run_simulation_batch(params))
        means.append(float(np.mean(ratios)))
        stds.append(float(np.std(ratios)))
        print(f"    {param_name}={val:.4g}  mean={means[-1]:.3f}  std={stds[-1]:.3f}")
    return means, stds


# --------------------------------------------------------------------------
# メイン処理
# --------------------------------------------------------------------------

def main():
    all_results = {}

    for param_name, values in SENSITIVITY_PARAMS.items():
        print(f"\n[感度分析] {param_name} スウィープ中...")
        means, stds = sweep_param(param_name, values)
        all_results[param_name] = {"values": values, "means": means, "stds": stds}

    # ------------------------------------------------------------------
    # グラフ出力（1パラメータ = 1サブプロット）
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(1, len(SENSITIVITY_PARAMS), figsize=(5 * len(SENSITIVITY_PARAMS), 4))

    for ax, (param_name, result) in zip(axes, all_results.items()):
        vals  = result["values"]
        means = result["means"]
        stds  = result["stds"]
        ax.errorbar(vals, means, yerr=stds, fmt="o-", capsize=5,
                    linewidth=2, markersize=7, color="#3b5998")
        ax.axhline(DEFAULT_PARAMS.get(param_name, 0), color="gray",
                   linestyle="--", linewidth=1.0, alpha=0.7, label="デフォルト値")
        ax.axhline(0.5, color="red", linestyle=":", linewidth=0.8, alpha=0.6)
        ax.set_xlabel(param_name, fontsize=11)
        ax.set_ylabel("最終協力率", fontsize=11)
        ax.set_ylim(0, 1)
        ax.set_title(f"{param_name}\n感度分析 (n={N_RUNS})", fontsize=11)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    fig.suptitle(f"パラメータ感度分析 — mutation_rate / max_age / reproduce_threshold\n"
                 f"(N_RUNS={N_RUNS}, N_STEPS={N_STEPS}, BASE_SEED={BASE_SEED})", fontsize=12)
    plt.tight_layout()
    out_path = os.path.join(FIGURES_DIR, "fig6_sensitivity.png")
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"\n-> {out_path} 保存完了")

    # CSV 出力
    rows = []
    for param_name, result in all_results.items():
        for val, mean, std in zip(result["values"], result["means"], result["stds"]):
            rows.append({"parameter": param_name, "value": val,
                         "mean_coop_ratio": mean, "std_coop_ratio": std,
                         "n_runs": N_RUNS})
    df = pd.DataFrame(rows)
    csv_path = os.path.join(os.path.dirname(__file__), "data", "sensitivity_results.csv")
    df.to_csv(csv_path, index=False)
    print(f"-> {csv_path} 保存完了\n")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
