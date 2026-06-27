"""
test_quick.py — 軽量・簡易版の最終テスト
グリッド10×10, エージェント50, ステップ10 で主要動作を一通り検証する。
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import traceback
import numpy as np
from model import SelfishGeneModel, DEFAULT_PARAMS
from agents import GeneAgent

PASS = "  [PASS]"
FAIL = "  [FAIL]"

# 共通の軽量パラメータ
LIGHT = {
    **DEFAULT_PARAMS,
    "width": 10,
    "height": 10,
    "n_agents": 50,
    "seed": 42,
}

results = []

def check(name, ok, detail=""):
    status = PASS if ok else FAIL
    msg = f"{status} {name}"
    if detail:
        msg += f" ({detail})"
    print(msg)
    results.append((name, ok))

# ============================================================
# 1. モデル初期化
# ============================================================
print("\n[1] モデル初期化テスト")
try:
    m = SelfishGeneModel(**LIGHT)
    check("SelfishGeneModel 生成", True)
    check("グリッドサイズ", m.grid.width == 10 and m.grid.height == 10,
          f"w={m.grid.width} h={m.grid.height}")
    n = len(m.agents)
    check("エージェント数 == 50", n == 50, f"n={n}")
    check("_cached_total 初期値", m._cached_total == 50, f"{m._cached_total}")
    check("_cached_coop_ratio 範囲 [0,1]",
          0.0 <= m._cached_coop_ratio <= 1.0, f"{m._cached_coop_ratio:.3f}")
except Exception as e:
    check("SelfishGeneModel 生成", False, str(e))
    traceback.print_exc()

# ============================================================
# 2. エージェント属性
# ============================================================
print("\n[2] エージェント属性テスト")
try:
    agent = next(iter(m.agents))
    check("strategy ∈ {0,1}", agent.strategy in (0, 1), f"strategy={agent.strategy}")
    check("energy > 0", agent.energy > 0, f"energy={agent.energy:.2f}")
    check("age == 0 (初期)", agent.age == 0)
    check("green_beard == bool", isinstance(agent.green_beard, bool))
except Exception as e:
    check("エージェント属性", False, str(e))

# ============================================================
# 3. 10ステップ実行（基本動作）
# ============================================================
print("\n[3] 10ステップ実行テスト")
try:
    m2 = SelfishGeneModel(**LIGHT)
    for i in range(10):
        m2.step()
    df = m2.datacollector.get_model_vars_dataframe()
    check("step() 10回完走", True)
    check("DataCollector 行数 == 11", len(df) == 11, f"rows={len(df)}")
    check("CoopRatio 範囲 [0,1]",
          (df["CoopRatio"] >= 0).all() and (df["CoopRatio"] <= 1).all())
    check("TotalAgents >= 0", (df["TotalAgents"] >= 0).all())
    check("MeanEnergy 存在", "MeanEnergy" in df.columns)
except Exception as e:
    check("10ステップ実行", False, str(e))
    traceback.print_exc()

# ============================================================
# 4. グリッドスナップショット
# ============================================================
print("\n[4] グリッドスナップショットテスト")
try:
    snap = m2.get_grid_snapshot()
    check("shape == (10,10)", snap.shape == (10, 10), f"shape={snap.shape}")
    check("値が {0,1,2} のみ",
          set(np.unique(snap)).issubset({0, 1, 2}), f"unique={np.unique(snap)}")
except Exception as e:
    check("グリッドスナップショット", False, str(e))

# ============================================================
# 5. 緑ひげモード（シナリオB）
# ============================================================
print("\n[5] 緑ひげモードテスト")
try:
    gb_params = {**LIGHT, "green_beard_enabled": True, "recognition_error_rate": 0.0}
    mg = SelfishGeneModel(**gb_params)
    for _ in range(5):
        mg.step()
    check("緑ひげモード 5ステップ完走", True)
    # 協力者は green_beard=True であるはず
    coops = [a for a in mg.agents if a.strategy == GeneAgent.COOPERATOR]
    check("協力者の green_beard==True",
          all(a.green_beard for a in coops),
          f"coops={len(coops)}")
except Exception as e:
    check("緑ひげモード", False, str(e))

# ============================================================
# 6. キャッシュ整合性
# ============================================================
print("\n[6] キャッシュ整合性テスト")
try:
    actual_coop = sum(1 for a in m2.agents if a.strategy == GeneAgent.COOPERATOR)
    actual_total = len(m2.agents)
    check("_cached_coop 一致", m2._cached_coop == actual_coop,
          f"cache={m2._cached_coop} actual={actual_coop}")
    check("_cached_total 一致", m2._cached_total == actual_total,
          f"cache={m2._cached_total} actual={actual_total}")
    expected_ratio = actual_coop / actual_total if actual_total > 0 else 0.0
    check("_cached_coop_ratio 一致",
          abs(m2._cached_coop_ratio - expected_ratio) < 1e-9,
          f"cache={m2._cached_coop_ratio:.4f} expected={expected_ratio:.4f}")
except Exception as e:
    check("キャッシュ整合性", False, str(e))

# ============================================================
# 結果サマリー
# ============================================================
print("\n" + "=" * 45)
passed = sum(1 for _, ok in results if ok)
total  = len(results)
print(f"テスト結果: {passed}/{total} PASS")
if passed == total:
    print("OK 全テスト合格")
else:
    failed = [name for name, ok in results if not ok]
    print(f"✗ 失敗: {failed}")
print("=" * 45)

sys.exit(0 if passed == total else 1)
