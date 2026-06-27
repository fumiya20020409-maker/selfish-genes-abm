"""
stat_test.py — Mann-Whitney U 検定スクリプト

raw_results.csv（個別試行の最終協力率）を読み込み、
各シナリオ内の条件ペアについて Mann-Whitney U 検定を実施し、
結果を stat_test_results.csv として出力する。

実行方法：
    cd selfish_genes
    python src/stat_test.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
from scipy.stats import mannwhitneyu

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_CSV  = os.path.join(DATA_DIR, "raw_results.csv")
OUT_CSV  = os.path.join(DATA_DIR, "stat_test_results.csv")


def mwu(a, b):
    """両側 Mann-Whitney U 検定。U 統計量と p 値を返す。"""
    stat, p = mannwhitneyu(a, b, alternative="two-sided")
    return float(stat), float(p)


def p_label(p):
    if p < 0.001:
        return "p < 0.001"
    elif p < 0.01:
        return "p < 0.01"
    elif p < 0.05:
        return "p < 0.05"
    else:
        return f"p = {p:.3f} (n.s.)"


def main():
    df = pd.read_csv(RAW_CSV)
    results = []

    def get(scenario):
        return df.loc[df["scenario"] == scenario, "final_coop_ratio"].values

    baseline = get("baseline")

    # ------------------------------------------------------------------
    # シナリオB：各条件 vs 緑ひげなし（= baseline と同値）
    # ------------------------------------------------------------------
    scenario_b = [
        ("e=0.0 (完全認識)", "e=0.0"),
        ("e=0.05",           "e=0.05"),
        ("e=0.10",           "e=0.10"),
        ("e=0.20",           "e=0.20"),
    ]
    ref_b = get("緑ひげなし")
    for scenario_key, label in scenario_b:
        a = get(scenario_key)
        if len(a) == 0:
            print(f"[警告] シナリオキー '{scenario_key}' がデータに見つかりません")
            continue
        u, p = mwu(a, ref_b)
        results.append({
            "scenario": "B",
            "condition_a": label,
            "condition_b": "緑ひげなし",
            "mean_a": np.mean(a),
            "mean_b": np.mean(ref_b),
            "U": u,
            "p_value": p,
            "significance": p_label(p),
        })
        print(f"  B: {label} vs 緑ひげなし  U={u:.0f}  {p_label(p)}")

    # 隣接条件間（e=0.0 vs e=0.20）
    a0  = get("e=0.0 (完全認識)")
    a20 = get("e=0.20")
    if len(a0) and len(a20):
        u, p = mwu(a0, a20)
        results.append({
            "scenario": "B",
            "condition_a": "e=0.0",
            "condition_b": "e=0.20",
            "mean_a": np.mean(a0),
            "mean_b": np.mean(a20),
            "U": u,
            "p_value": p,
            "significance": p_label(p),
        })
        print(f"  B: e=0.0 vs e=0.20  U={u:.0f}  {p_label(p)}")

    # ------------------------------------------------------------------
    # シナリオA：各条件 vs ベースケース (rate=1.0)
    # ------------------------------------------------------------------
    scenario_a_rates = [0.2, 0.5, 2.0, 3.0, 5.0]
    ref_a = get("A_rate1.0")
    if len(ref_a) == 0:
        ref_a = baseline  # フォールバック
    for rr in scenario_a_rates:
        a = get(f"A_rate{rr}")
        if len(a) == 0:
            continue
        u, p = mwu(a, ref_a)
        results.append({
            "scenario": "A",
            "condition_a": f"rate={rr}",
            "condition_b": "rate=1.0（ベース）",
            "mean_a": np.mean(a),
            "mean_b": np.mean(ref_a),
            "U": u,
            "p_value": p,
            "significance": p_label(p),
        })
        print(f"  A: rate={rr} vs rate=1.0  U={u:.0f}  {p_label(p)}")

    # ------------------------------------------------------------------
    # シナリオC：各条件 vs ベースケース (d=0.1)
    # ------------------------------------------------------------------
    scenario_c = [
        ("固定 d=0.0",  "d=0.0"),
        ("中移動 d=0.3", "d=0.3"),
        ("高移動 d=0.9", "d=0.9"),
    ]
    ref_c = get("低移動 d=0.1")
    if len(ref_c) == 0:
        ref_c = baseline
    for scenario_key, label in scenario_c:
        a = get(scenario_key)
        if len(a) == 0:
            print(f"[警告] シナリオキー '{scenario_key}' がデータに見つかりません")
            continue
        u, p = mwu(a, ref_c)
        results.append({
            "scenario": "C",
            "condition_a": label,
            "condition_b": "d=0.1（ベース）",
            "mean_a": np.mean(a),
            "mean_b": np.mean(ref_c),
            "U": u,
            "p_value": p,
            "significance": p_label(p),
        })
        print(f"  C: {label} vs d=0.1  U={u:.0f}  {p_label(p)}")

    # ------------------------------------------------------------------
    # CSV 出力
    # ------------------------------------------------------------------
    out_df = pd.DataFrame(results)
    out_df.to_csv(OUT_CSV, index=False)
    print(f"\n-> {OUT_CSV} 保存完了")
    print()
    print(out_df[["scenario", "condition_a", "condition_b",
                  "mean_a", "mean_b", "U", "p_value", "significance"]].to_string(index=False))


if __name__ == "__main__":
    main()
