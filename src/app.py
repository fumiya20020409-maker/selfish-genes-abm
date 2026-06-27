"""
app.py — Solaraインタラクティブダッシュボード
実行方法：
    cd selfish_genes
    python -m solara run app.py
"""

import time
import solara
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Meiryo"
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.figure import Figure
from matplotlib.patches import Patch
import numpy as np
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from model import SelfishGeneModel, DEFAULT_PARAMS

# ==========================================================================
# シナリオプリセット定義
# ==========================================================================

PRESETS = {
    "── プリセットを選択 ──": None,
    "📋 ベースケース": {
        "params": DEFAULT_PARAMS,
        "description": (
            "**ベースケース（標準設定）**\n\n"
            "すべてのパラメータが論文の基準値。"
            "移動性・突然変異率・リソースが中程度の標準的な環境。"
            "協力者と裏切り者がどちらが優勢になるかを観察する出発点。"
        ),
    },
    "🌿 シナリオA：リソース豊富": {
        "params": {**DEFAULT_PARAMS, "resource_recovery_rate": 3.0},
        "description": (
            "**シナリオA — リソース豊富環境**\n\n"
            "リソース回復速度を 3.0 に設定。食料や資源が十分にある豊かな環境を模倣。"
            "エージェントは繁殖しやすくなるため個体数が急増する。"
            "裏切り者が増殖しやすい一方、協力者クラスターも維持されやすい。"
            "資源の豊富さが協力の進化に有利か不利かを検証する。"
        ),
    },
    "🏜️ シナリオA：リソース枯渇": {
        "params": {**DEFAULT_PARAMS, "resource_recovery_rate": 0.2},
        "description": (
            "**シナリオA — リソース枯渇環境**\n\n"
            "リソース回復速度を 0.2 に設定。食料や資源が極端に乏しい過酷な環境。"
            "ほとんどのエージェントがエネルギー不足で死滅するため、"
            "少数の高適応度個体のみが生き残る。"
            "過酷な環境が利己的戦略と協力戦略のどちらに有利かを検証する。"
        ),
    },
    "🟢 シナリオB：緑ひげ完全認識": {
        "params": {**DEFAULT_PARAMS, "green_beard_enabled": True, "recognition_error_rate": 0.0},
        "description": (
            "**シナリオB — 緑ひげ効果（完全認識）**\n\n"
            "協力者は「緑ひげマーカー」を持ち、同じマーカーを持つ相手にのみ協力する。"
            "認識誤りがゼロのため、協力者は仲間を完璧に識別できる。"
            "ドーキンスが『利己的な遺伝子』で提唱した緑ひげ効果の理想的条件。"
            "協力遺伝子が血縁淘汰なしに広まるかを観察する。"
        ),
    },
    "🟡 シナリオB：緑ひげ誤認10%": {
        "params": {**DEFAULT_PARAMS, "green_beard_enabled": True, "recognition_error_rate": 0.1},
        "description": (
            "**シナリオB — 緑ひげ効果（認識誤り10%）**\n\n"
            "緑ひげマーカーの認識が 10% の確率で誤る設定。"
            "協力者が裏切り者を仲間と誤認して協力してしまう（搾取される）。"
            "認識精度の低下が緑ひげ効果の安定性を崩すかを検証する。"
        ),
    },
    "🔴 シナリオB：緑ひげ誤認20%": {
        "params": {**DEFAULT_PARAMS, "green_beard_enabled": True, "recognition_error_rate": 0.2},
        "description": (
            "**シナリオB — 緑ひげ効果（認識誤り20%）**\n\n"
            "認識誤り率が 20% まで上昇した設定。"
            "5回に1回は敵味方を誤認するほど不正確な認識。"
            "理論的には誤り率が高いほど緑ひげ効果は崩壊し、裏切り者が優勢になると予測される。"
        ),
    },
    "🧱 シナリオC：固定（移動なし）": {
        "params": {**DEFAULT_PARAMS, "diffusion_rate": 0.0},
        "description": (
            "**シナリオC — 完全固定（diffusion_rate=0.0）**\n\n"
            "エージェントが一切移動しない。生まれた場所で一生を過ごす。"
            "空間的なクラスター構造が最も強く維持される。"
            "協力者は隣人と協力し続けることでクラスターを形成し、裏切り者の侵入を防ぐ。"
            "空間構造が協力の維持に最も有利な条件。"
        ),
    },
    "🚶 シナリオC：低移動（d=0.1）": {
        "params": {**DEFAULT_PARAMS, "diffusion_rate": 0.1},
        "description": (
            "**シナリオC — 低移動（diffusion_rate=0.1）**\n\n"
            "各ステップで 10% の確率で隣のセルに移動する。ベースケースと同じ設定。"
            "空間クラスターはほぼ維持されるが、わずかな移動により協力者が新しい領域に広がれる。"
            "先行研究で最も協力率が高くなりやすいとされる移動性レベル。"
        ),
    },
    "🏃 シナリオC：高移動（d=0.9）": {
        "params": {**DEFAULT_PARAMS, "diffusion_rate": 0.9},
        "description": (
            "**シナリオC — 高移動（diffusion_rate=0.9）**\n\n"
            "各ステップで 90% の確率でランダムに移動する。ほぼランダム拡散の状態。"
            "空間クラスターが形成されず、well-mixed（完全混合）に近い状態。"
            "理論的には移動性が高いほど協力率が低下する（裏切り者が搾取しやすくなる）。"
        ),
    },
}

PRESET_LABELS = list(PRESETS.keys())

# ==========================================================================
# パラメータ説明
# ==========================================================================

PARAM_DESCRIPTIONS = {
    "diffusion_rate": {
        "label": "移動性 (diffusion_rate)",
        "range": "0.0〜1.0",
        "increase": "↑ 増やすと：より広く移動 → 空間クラスターが崩れ、裏切り者が搾取しやすくなる",
        "decrease": "↓ 減らすと：固定に近づく → 協力者クラスターが形成され、裏切り者の侵入を防ぎやすくなる",
    },
    "mutation_rate": {
        "label": "突然変異率 (mutation_rate)",
        "range": "0.0〜0.2",
        "increase": "↑ 増やすと：繁殖時に戦略が反転しやすくなる → どちらも支配的になりにくい",
        "decrease": "↓ 減らすと：戦略が安定して継承される → 優勢な戦略がより純粋に増殖する",
    },
    "resource_recovery_rate": {
        "label": "リソース回復速度 (resource_recovery_rate)",
        "range": "0.1〜5.0",
        "increase": "↑ 増やすと：全員の基礎エネルギーが増え繁殖しやすくなる（環境リソース量の操作）",
        "decrease": "↓ 減らすと：エネルギー不足で多くが死滅 → 個体数が減少し、クラスターも崩壊しやすくなる",
    },
    "coop_bonus_rate": {
        "label": "公共財ボーナス (coop_bonus_rate)",
        "range": "0.0〜2.0",
        "increase": "↑ 増やすと：協力者が追加エネルギーを多く得る → 協力クラスターが形成されやすくなる",
        "decrease": "↓ 減らすと：協力者の優遇が弱まる → 裏切り者のペイオフ優位が支配的になりやすい",
    },
    "initial_coop_ratio": {
        "label": "初期協力率 (initial_coop_ratio)",
        "range": "0.0〜1.0",
        "increase": "↑ 増やすと：最初から協力者が多い → クラスターが形成されやすく協力が優勢になりやすい",
        "decrease": "↓ 減らすと：最初から裏切り者が多い → 協力者が少数派として生き残れるかを試す",
    },
    "recognition_error_rate": {
        "label": "認識誤り率 ε（緑ひげ効果のみ有効）",
        "range": "0.0〜0.5",
        "increase": "↑ 増やすと：敵味方の誤認が増える → 緑ひげ効果が崩壊し、裏切り者に搾取されやすくなる",
        "decrease": "↓ 減らすと：認識が精確になる → 緑ひげ効果が安定し、仲間を選んで協力できる",
    },
}

# ==========================================================================
# リアクティブな状態変数
# ==========================================================================

diffusion_rate    = solara.reactive(float(DEFAULT_PARAMS["diffusion_rate"]))
mutation_rate     = solara.reactive(float(DEFAULT_PARAMS["mutation_rate"]))
resource_rate     = solara.reactive(float(DEFAULT_PARAMS["resource_recovery_rate"]))
coop_bonus_rate   = solara.reactive(float(DEFAULT_PARAMS["coop_bonus_rate"]))
green_beard       = solara.reactive(bool(DEFAULT_PARAMS["green_beard_enabled"]))
recognition_error = solara.reactive(float(DEFAULT_PARAMS["recognition_error_rate"]))
initial_coop      = solara.reactive(float(DEFAULT_PARAMS["initial_coop_ratio"]))
n_agents_val      = solara.reactive(int(DEFAULT_PARAMS["n_agents"]))

model_state        = solara.reactive(None)
step_count         = solara.reactive(0)
coop_history       = solara.reactive([])
total_history      = solara.reactive([])
selected_preset    = solara.reactive(PRESET_LABELS[0])
preset_description = solara.reactive("")


def make_model():
    return SelfishGeneModel(
        width=50, height=50,
        n_agents=n_agents_val.value,
        initial_coop_ratio=initial_coop.value,
        diffusion_rate=diffusion_rate.value,
        mutation_rate=mutation_rate.value,
        resource_recovery_rate=resource_rate.value,
        coop_bonus_rate=coop_bonus_rate.value,
        green_beard_enabled=green_beard.value,
        recognition_error_rate=recognition_error.value,
        seed=int(time.time()) % 2**31,
    )


def reset_model():
    model_state.value = make_model()
    step_count.value = 0
    coop_history.value = [model_state.value._coop_ratio()]
    total_history.value = [len(model_state.value.agents)]


def do_steps(n: int):
    if model_state.value is None:
        reset_model()
    m = model_state.value
    actual = 0
    for _ in range(n):
        m.step()
        actual += 1
        if len(m.agents) == 0:
            break
    # リストの再生成を1回にまとめる（nが大きいほど効果大）
    step_count.value    = step_count.value + actual
    coop_history.value  = coop_history.value  + [m._coop_ratio()]
    total_history.value = total_history.value + [len(m.agents)]


def apply_preset(label: str):
    selected_preset.value = label
    preset = PRESETS.get(label)
    if preset is None:
        preset_description.value = ""
        return
    p = preset["params"]
    diffusion_rate.value    = float(p["diffusion_rate"])
    mutation_rate.value     = float(p["mutation_rate"])
    resource_rate.value     = float(p["resource_recovery_rate"])
    coop_bonus_rate.value   = float(p["coop_bonus_rate"])
    green_beard.value       = bool(p["green_beard_enabled"])
    recognition_error.value = float(p["recognition_error_rate"])
    initial_coop.value      = float(p["initial_coop_ratio"])
    n_agents_val.value      = int(p["n_agents"])
    preset_description.value = preset["description"]
    reset_model()


# ==========================================================================
# 可視化コンポーネント
# ==========================================================================

@solara.component
def GridView():
    model = model_state.value
    if model is None:
        solara.Text("「🔄 リセット」または「▶ ステップ実行」を押してください")
        return
    snapshot = model.get_grid_snapshot()
    fig = Figure(figsize=(5.5, 5.5))
    ax = fig.add_subplot(111)
    cmap = mcolors.ListedColormap(["#f5f5f5", "#3498db", "#e74c3c"])
    ax.imshow(snapshot.T, cmap=cmap, vmin=0, vmax=2, origin="lower")
    coop_r = model._coop_ratio()
    total  = len(model.agents)
    ax.set_title(
        f"Step {step_count.value}  |  協力率: {coop_r:.1%}  |  個体数: {total}",
        fontsize=11, pad=8,
    )
    ax.set_xlabel("X軸"); ax.set_ylabel("Y軸")
    legend_elements = [
        Patch(facecolor="#3498db", label="協力者 (Cooperator)"),
        Patch(facecolor="#e74c3c", label="裏切り者 (Defector)"),
        Patch(facecolor="#f5f5f5", edgecolor="#ccc", label="空セル"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    solara.FigureMatplotlib(fig)
    plt.close(fig)


@solara.component
def CoopChart():
    history = coop_history.value
    if len(history) < 2:
        return
    fig = Figure(figsize=(6.5, 3))
    ax = fig.add_subplot(111)
    ax.plot(history, color="#3498db", linewidth=1.8, label="協力率")
    ax.fill_between(range(len(history)), history, alpha=0.15, color="#3498db")
    ax.axhline(0.5, color="#e74c3c", linestyle="--", linewidth=1.0, alpha=0.6, label="50%ライン")
    ax.set_ylim(0, 1)
    ax.set_xlabel("記録ポイント（ステップ実行ごと）")
    ax.set_ylabel("協力率")
    ax.set_title("協力率の推移")
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    solara.FigureMatplotlib(fig)
    plt.close(fig)


@solara.component
def PopulationChart():
    history = total_history.value
    coop_h  = coop_history.value
    if len(history) < 2:
        return
    coop_n   = [int(h * t) for h, t in zip(coop_h, history)]
    defect_n = [t - c for t, c in zip(history, coop_n)]
    fig = Figure(figsize=(6.5, 2.8))
    ax = fig.add_subplot(111)
    ax.stackplot(range(len(history)), coop_n, defect_n,
                 labels=["協力者", "裏切り者"],
                 colors=["#3498db", "#e74c3c"], alpha=0.75)
    ax.set_xlabel("記録ポイント")
    ax.set_ylabel("個体数")
    ax.set_title("戦略別個体数の推移")
    ax.legend(loc="upper left", fontsize=9); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    solara.FigureMatplotlib(fig)
    plt.close(fig)


@solara.component
def ParamCard(key: str):
    d = PARAM_DESCRIPTIONS[key]
    with solara.Column(
        style={
            "background": "#f8f9fa",
            "borderLeft": "3px solid #3498db",
            "padding": "8px 12px",
            "marginBottom": "4px",
            "marginTop": "8px",
            "borderRadius": "0 4px 4px 0",
        }
    ):
        solara.Markdown(f"**{d['label']}** `{d['range']}`")
        solara.Markdown(
            f"<span style='color:#27ae60;font-size:12px'>{d['increase']}</span>  \n"
            f"<span style='color:#e74c3c;font-size:12px'>{d['decrease']}</span>"
        )


# ==========================================================================
# メインページ
# ==========================================================================

@solara.component
def Page():
    solara.Title("利己的な遺伝子シミュレーション")

    # ヘッダー
    solara.Markdown(
        "# 🧬 利己的な遺伝子シミュレーション\n"
        "空間的囚人のジレンマモデルによる協力遺伝子と裏切り遺伝子の進化シミュレーション"
    )
    solara.Markdown("---")

    with solara.Row(style={"alignItems": "flex-start", "gap": "24px"}):

        # ============================
        # 左カラム：コントロールパネル
        # ============================
        with solara.Column(style={"width": "380px", "minWidth": "380px"}):

            # --- シナリオプリセット ---
            solara.Markdown("## 🎯 シナリオプリセット")
            solara.Markdown(
                "プリセットを選ぶとパラメータが自動設定されリセットされます。",
                style={"fontSize": "13px", "color": "#666"},
            )
            solara.Select(
                label="シナリオを選択",
                value=selected_preset,
                values=PRESET_LABELS,
                on_value=apply_preset,
            )

            if preset_description.value:
                solara.Markdown(
                    preset_description.value,
                    style={
                        "background": "#e8f4fd",
                        "borderLeft": "4px solid #3498db",
                        "padding": "10px 14px",
                        "marginTop": "8px",
                        "fontSize": "13px",
                        "borderRadius": "0 4px 4px 0",
                    },
                )

            solara.Markdown("---")

            # --- ステップ実行ボタン ---
            solara.Markdown("## ▶️ ステップ実行")
            solara.Markdown(
                "ボタンを押すと指定ステップ分シミュレーションが進みます。  \n"
                "グラフは実行完了後に更新されます。",
                style={"fontSize": "13px", "color": "#666"},
            )

            with solara.Row(style={"flexWrap": "wrap", "gap": "8px"}):
                solara.Button("🔄 リセット",  on_click=reset_model,              color="default")
                solara.Button("＋1ステップ",   on_click=lambda: do_steps(1),     color="primary")
                solara.Button("＋10ステップ",  on_click=lambda: do_steps(10),    color="primary")
                solara.Button("＋50ステップ",  on_click=lambda: do_steps(50),    color="primary")
                solara.Button("＋100ステップ", on_click=lambda: do_steps(100),   color="primary")
                solara.Button("＋300ステップ（論文用）", on_click=lambda: do_steps(300), color="secondary")

            solara.Markdown(
                "⚠️ **＋300ステップ** は数分かかることがあります。",
                style={"fontSize": "12px", "color": "#e67e22", "marginTop": "4px"},
            )

            if model_state.value is not None:
                total  = len(model_state.value.agents)
                coop_r = model_state.value._coop_ratio()
                solara.Markdown(
                    f"**現在のステップ数：** {step_count.value}　"
                    f"**協力率：** {coop_r:.1%}　"
                    f"**個体数：** {total}",
                    style={"marginTop": "8px", "fontSize": "14px"},
                )

            solara.Markdown("---")

            # --- パラメータ調整 ---
            solara.Markdown("## ⚙️ パラメータ調整")
            solara.Markdown(
                "スライダーで値を変更後、**「🔄 リセット」を押す**と新しい設定で開始されます。",
                style={"fontSize": "13px", "color": "#666"},
            )

            ParamCard("diffusion_rate")
            solara.SliderFloat(
                label=f"diffusion_rate = {diffusion_rate.value:.2f}",
                value=diffusion_rate, min=0.0, max=1.0, step=0.05,
            )

            ParamCard("mutation_rate")
            solara.SliderFloat(
                label=f"mutation_rate = {mutation_rate.value:.3f}",
                value=mutation_rate, min=0.0, max=0.2, step=0.005,
            )

            ParamCard("resource_recovery_rate")
            solara.SliderFloat(
                label=f"resource_recovery_rate = {resource_rate.value:.1f}",
                value=resource_rate, min=0.1, max=5.0, step=0.1,
            )

            ParamCard("coop_bonus_rate")
            solara.SliderFloat(
                label=f"coop_bonus_rate = {coop_bonus_rate.value:.2f}",
                value=coop_bonus_rate, min=0.0, max=2.0, step=0.05,
            )

            ParamCard("initial_coop_ratio")
            solara.SliderFloat(
                label=f"initial_coop_ratio = {initial_coop.value:.2f}",
                value=initial_coop, min=0.0, max=1.0, step=0.05,
            )

            solara.Markdown("---")
            solara.Markdown("## 🟢 緑ひげ効果（シナリオB）")
            solara.Markdown(
                "協力者が「緑ひげマーカー」で仲間を識別し、選択的に協力する。  \n"
                "ドーキンスの血縁認識理論のシミュレーション。",
                style={"fontSize": "13px", "color": "#666"},
            )
            solara.Checkbox(label="緑ひげ効果を有効化", value=green_beard)

            if green_beard.value:
                ParamCard("recognition_error_rate")
                solara.SliderFloat(
                    label=f"recognition_error_rate ε = {recognition_error.value:.2f}",
                    value=recognition_error, min=0.0, max=0.5, step=0.01,
                )

        # ============================
        # 右カラム：可視化
        # ============================
        with solara.Column(style={"flex": "1", "minWidth": "0"}):

            solara.Markdown("## 🗺️ グリッド表示")
            solara.Markdown(
                "🔵 **青：協力者（Cooperator）** — 仲間と協力してリソースを共有する遺伝子戦略  \n"
                "🔴 **赤：裏切り者（Defector）** — 協力せず一方的にリソースを搾取する遺伝子戦略  \n"
                "⬜ **白：空セル** — エージェントが存在しないセル",
                style={"fontSize": "13px", "marginBottom": "8px"},
            )
            GridView()

            solara.Markdown("---")
            solara.Markdown("## 📈 協力率の推移")
            solara.Markdown(
                "ステップを進めるたびにプロットが追加されます。"
                "赤破線（50%）より上なら協力者が優勢。",
                style={"fontSize": "13px", "color": "#666"},
            )
            CoopChart()

            solara.Markdown("---")
            solara.Markdown("## 👥 戦略別個体数の推移")
            solara.Markdown(
                "青（協力者）と赤（裏切り者）の個体数の積み上げグラフ。"
                "個体群全体の消長も確認できる。",
                style={"fontSize": "13px", "color": "#666"},
            )
            PopulationChart()
