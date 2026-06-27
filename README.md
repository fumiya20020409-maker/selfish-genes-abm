# 利己的な遺伝子シミュレーション
**Selfish Genes Simulation — Agent-Based Model using Mesa**

> AIエージェント（IBM Bob）への指示だけで、**週末2日**で作った研究シミュレーションです。

---

## まずどれを読めばいいか

| あなたは | 読むファイル |
|---|---|
| 「AIエージェントでどう作ったか」が知りたい | [PROCESS.md](PROCESS.md) |
| シミュレーションを動かしてみたい | このREADMEの「動かし方」へ |
| 論文の中身を読みたい | [docs/paper.md](docs/paper.md) |
| コードの改訂経緯を追いたい | [CHANGELOG.md](CHANGELOG.md) |

---

## このリポジトリは何か

「協力する個体」と「裏切る個体」が 50×50 のグリッド上で生存競争を繰り広げます。
空間構造・血縁認識・移動性という3つの条件を変えながら、**協力行動がどう維持されるか** を観察します。

理論的背景は進化ゲーム理論（Nowak & May 1992）ですが、**専門知識がなくても動かして試せます。**

---

## 動かし方

```bash
# セットアップ（初回のみ）
pip install -r requirements.txt

# インタラクティブダッシュボード（おすすめ）
cd src
solara run app.py
# → ブラウザで http://localhost:8765 が開く。スライダーでパラメータをリアルタイムに変更できる。

# 論文用グラフを再現する（約7〜8分）
cd src
python run_analysis.py
# → data/figures/ に図1〜5が出力される
```

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

## ファイル構成

```
/
├── README.md        ← いまここ。全体の入口
├── PROCESS.md       ← AIエージェントでの制作プロセス記録（読み物）
├── CHANGELOG.md     ← Bobとの改訂履歴
├── requirements.txt ← 依存ライブラリ
│
├── docs/
│   └── paper.md     ← 論文本文
│
├── src/（シミュレーション本体）
│   ├── agents.py    ← エージェントの定義
│   ├── model.py     ← モデルの定義（実験設計の核）
│   ├── app.py       ← インタラクティブダッシュボード
│   ├── run_analysis.py  ← 論文用グラフ生成（図1〜5）
│   └── batch_run.py     ← 感度分析（図6）
│
├── notebooks/
│   └── analysis.ipynb   ← Jupyter Notebook版
│
└── data/
    └── figures/     ← グラフ出力先（run_analysis.py 実行後に生成）
```

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
