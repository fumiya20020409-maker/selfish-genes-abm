# 利己的な遺伝子シミュレーション
**Selfish Genes Simulation — Agent-Based Model using Mesa**

> **これはAIエージェント（IBM Bob）への指示だけで、週末2日で作った研究シミュレーションです。**  
> 作り方の記録は [HOW_I_BUILT_THIS.md](HOW_I_BUILT_THIS.md) を参照してください。

---

## 何をするシミュレーションか

「協力する個体」と「裏切る個体」が 50×50 のグリッド上で生存競争を繰り広げます。  
空間構造・血縁認識・移動性という3つの条件を変えながら、**協力行動がどう維持されるか（または崩壊するか）** を観察します。

理論的背景は進化ゲーム理論（Nowak & May 1992, Hamilton 1964）ですが、  
**生物学の専門知識がなくても動かして試せます。**

---

## 動かし方

### セットアップ

```bash
pip install -r requirements.txt
```

### インタラクティブダッシュボード（おすすめ）

```bash
solara run app.py
```

ブラウザで `http://localhost:8765` が開きます。スライダーでパラメータをリアルタイムに変えながら実験できます。

### 論文用グラフを再現する

```bash
python run_analysis.py
```

`data/figures/` に図1〜5が出力されます（全実験で約7〜8分）。

---

## 3つの実験シナリオ

| シナリオ | 何を変えるか | 問い |
|---|---|---|
| A | リソース回復率 | 環境が豊かだと協力は増えるか？ |
| B | 血縁認識（緑ひげ効果） | 仲間を見分けられると協力は安定するか？ |
| C | 移動性 | 動き回ると協力クラスタは壊れるか？ |

ゲームのルール（囚人のジレンマ）：

| 自分 ＼ 相手 | 協力 (C) | 裏切り (D) |
|---|---|---|
| **協力 (C)** | 3.0 | 0.0 |
| **裏切り (D)** | 5.0 | 1.0 |

---

## プロジェクト構成

```
selfish_genes/
├── HOW_I_BUILT_THIS.md  # AIエージェントでの制作プロセス記録
├── agents.py            # GeneAgent クラス
├── model.py             # SelfishGeneModel クラス（ODD プロトコル準拠）
├── app.py               # Solara インタラクティブダッシュボード
├── run_analysis.py      # 論文用グラフ生成スクリプト（図1〜5）
├── batch_run.py         # パラメータ感度分析スクリプト（図6）
├── paper_draft.md       # 論文本文
├── CHANGELOG.md         # Bobとの改訂履歴
├── requirements.txt     # 依存ライブラリ
├── notebooks/
│   └── analysis.ipynb   # Jupyter Notebook版
└── data/
    ├── figures/                  # グラフ出力先
    ├── summary_results.csv       # 実験結果サマリー
    └── sensitivity_results.csv   # 感度分析結果
```

---

## 実行時間の目安

| 処理 | 時間 |
|---|---|
| 1試行 × 500ステップ | 約 1.2 秒 |
| `run_analysis.py` 全体（N_RUNS=20） | 約 7〜8 分 |
| `batch_run.py` 感度分析（N_RUNS=10） | 約 3〜4 分 |

---

## 動作環境

| ライブラリ | バージョン |
|---|---|
| Python | 3.13.x |
| Mesa | 3.5.1 |
| matplotlib | 3.11.0 |
| pandas | 3.0.3 |
| solara | 1.57.6 |
| numpy | 2.4.6 |

---

## 参考文献

- Dawkins, R. (1976). *The Selfish Gene*. Oxford University Press.
- Nowak, M. A., & May, R. M. (1992). Evolutionary games and spatial chaos. *Nature*, 359, 826–829.
- Hamilton, W. D. (1964). The genetical evolution of social behaviour. *Journal of Theoretical Biology*, 7(1), 1–16.
- Grimm, V., et al. (2020). The ODD protocol. *JASSS*, 23(2), 7.
