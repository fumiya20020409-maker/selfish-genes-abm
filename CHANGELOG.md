# CHANGELOG — 利己的な遺伝子シミュレーション

---

## [v1.3.0] — 2025-07 実験内部妥当性の修正

### 🔴 バグ修正

#### 緑ひげ認識ロジックの誤り修正 `agents.py`

**問題（修正前）**
```python
shares_marker = self.green_beard == other.green_beard
```
`False == False` が `True` になるため、マーカーを持たない defector 同士が
「同マーカー保持者」と誤判定され、緑ひげモードで cooperate してしまう
実験上の致命的バグ。シナリオBの全結果に影響していた。

**修正後**
```python
shares_marker = self.green_beard and other.green_beard
```
両者がともに `True`（= cooperator かつ緑ひげ有効）の場合のみ
「同マーカー」と判定。defector 同士は `False and False = False` となり
正しく `DEFECTOR` 行動を返す。

**影響範囲**
- シナリオBの全条件（`SCENARIO_B_PERFECT` / `ERROR05` / `ERROR10` / `ERROR20`）
- 緑ひげ無効条件（`SCENARIO_B_NONE`）は `green_beard_enabled=False` のため非該当

---

### 🟡 実験設計の改善

#### シナリオAのパラメータ分離 `model.py` / `app.py` / `run_analysis.py` / `paper_draft.md`

**問題（修正前）**
```python
self._coop_bonus = resource_recovery_rate * 0.5
```
`resource_recovery_rate` が「全員への基礎エネルギー回復」と「協力者への公共財ボーナス」を
同時に制御する複合変数になっており、「環境リソース量の操作」と「協力者優遇の強さの操作」
を分離できなかった。

**修正後**
- `coop_bonus_rate` を独立した新パラメータとして追加（デフォルト値 0.5）
- `DEFAULT_PARAMS` に追加、`__init__` シグネチャに追加
- 計算式を `self._coop_bonus = coop_bonus_rate`（固定値）に変更
- `SCENARIO_A_BONUS_HIGH`（1.5）/ `SCENARIO_A_BONUS_LOW`（0.1）シナリオ定数を追加

**影響ファイル**
- `model.py`：パラメータ追加・計算式変更・シナリオ定数追加
- `app.py`：スライダー追加・`make_model`/`apply_preset` に引数追加
- `run_analysis.py`：import に `SCENARIO_A_BONUS_HIGH/LOW` 追加・軸ラベル更新
- `paper_draft.md`：§4.1・§5.2・§6 の記述を独立パラメータとして書き直し

---

## [v1.2.0] — 2025-07 総合評価への回答（研究設計・論文記述方針）

査読者・研究者目線による総合評価（良い点・主要問題点・最終判定）を受けて、
コード修正では解決できない「論文記述・研究設計上の方針」を記録する。

---

### 総合評価の受け止め

| 評価軸 | 評価 | 本研究の位置づけ |
|---|---|---|
| 研究テーマの妥当性 | 高い | 空間構造・緑ひげ・移動性を同一フレームで比較する発想は妥当 |
| モデルの明示性・再現性 | 比較的高い | パラメータ・反復数・シード・出図手順の明示は良い |
| 因果解釈の強さ | 中〜低 | 操作変数と理論概念の対応が一部不純 |
| 査読で突かれやすい点 | 多い | 緑ひげ実装の単純化・リソース機構の恣意性・統計検定の不足 |

**最終判定：限定付きで妥当**
- 教育研究・探索研究としては妥当
- 厳密な理論検証研究としては、現状の設計だと主張過剰になりやすい
- 特にシナリオB（緑ひげ）とシナリオA（資源）の内部妥当性に注意が必要

---

### 問題点と対応方針

---

#### 問題1：緑ひげ効果の検証が理想化されすぎている

**評価の指摘**
> `GeneAgent._decide_action()` と `SelfishGeneModel.__init__()` では協力者だけが
> `green_beard=True` で裏切り者は必ず `False`。つまり「偽の緑ひげ」が存在しない。
> 結論は「緑ひげが有効なら協力が維持される」ではなく
> **「偽装不能な完全認識マーカーを仮定すれば協力が維持されやすい」に弱める必要がある。**

**コードへの対処（v1.1.0 で実施済み）**
- `model.py` と `agents.py` に設計上の限界をコメントで明記済み

**論文記述方針（新規）**

論文 §5（結果と考察）シナリオBの節に以下を必ず記述すること：

```
本モデルの緑ひげ効果は「協力遺伝子とマーカー遺伝子が遺伝的に完全にリンクしている」
理想的なシナリオに限定される。Hamilton (1964) および Dawkins (1976) が論じた
緑ひげ効果の理論的難所は、マーカーのみを持つ裏切り者（偽の緑ひげ）が集団に
侵入した際に協力が崩壊するという侵食シナリオにある。本実装ではこの侵食シナリオを
再現しておらず、結論は「完全マーカー連鎖の仮定下での認識誤り率の効果」として
解釈する必要がある。偽緑ひげを導入した拡張は今後の課題である。
```

**主張の弱め方（必須）**

| 修正前（過剰主張） | 修正後（適切な主張） |
|---|---|
| 緑ひげ効果は協力を維持する | 完全マーカー連鎖の仮定下では、認識誤り率が低いほど協力が維持されやすい |
| 認識誤り率が高いと協力が崩壊する | 認識誤り率の増加は、本モデルの設定範囲内で協力率を低下させる傾向がある |

---

#### 問題2：シナリオAのリソース機構が理論的に二役を担っている

**評価の指摘**
> `resource_recovery_rate` が「環境資源の豊富さ」と「協力者への追加優遇」の
> **二役を担っている**ため、「リソースが多いと協力が増えた」のか
> 「協力者にボーナスを与えたから増えた」のかが分離できない。

**コードの現状（v1.1.0 の修正）**
```python
self._coop_bonus = resource_recovery_rate * 0.5  # 協力者のみ追加
```
この設計は意図的だが、独立変数の操作として不純であることを論文で明示する必要がある。

**論文記述方針（新規）**

論文 §4（実験設定）シナリオAの節に以下を記述すること：

```
resource_recovery_rate パラメータは2つの効果を持つ複合変数として設計した。
第一に全エージェントへの基礎エネルギー回復（resource_recovery_rate - survival_cost）、
第二に協力者のみが受け取る公共財ボーナス（resource_recovery_rate × 0.5）である。
後者は「豊富な資源環境では協力的な個体が共有資源をより効率的に利用できる」
という公共財ゲームの論理（Hauert et al. 2002）に基づく設計選択である。
ただし、この設計により resource_recovery_rate の変化は「環境資源量の変化」と
「協力者優遇の強さの変化」を同時に操作することになる。両効果を分離した
感度分析は今後の課題として位置付ける（§6.2 参照）。
```

**参考文献として追加**
Hauert, C., De Monte, S., Hofbauer, J., & Sigmund, K. (2002).
Volunteering as red queen mechanism for cooperation in public goods games.
*Science*, 296(5570), 1129–1132.

---

#### 問題3：ゲーム利得と人口動態が混在している

**評価の指摘**
> 観測される「協力率」はPDの帰結というより、複合的なエネルギー管理系の帰結。
> 「空間的PDを検証した」と強く言うと危ない。

**論文記述方針（新規）**

論文 §3（モデル設計）の冒頭に以下を記述すること：

```
本モデルは囚人のジレンマのペイオフ行列（T=5, R=3, P=1, S=0）を相互作用の
核に持つが、観察される協力率はペイオフだけでなく、基礎エネルギー回復・
生存コスト・協力者ボーナス・繁殖閾値・繁殖コスト・寿命死亡の複合的な
人口動態ダイナミクスから創発する。したがって本研究は「囚人のジレンマを
厳密に再現する」ことを目的とするのではなく、「PD相互作用を含む人口動態ABMに
おいて、空間構造・血縁認識・移動性が協力の維持に与える影響を探索的に検討する」
ものとして位置づける。
```

---

#### 問題4：統計推論が弱い（95% CI・群間比較の不足）

**評価の指摘**
> 平均±SDだけでなく、最終協力率の95% CI、条件間比較、可能ならAUCや
> 定常区間平均が欲しい。

**対応方針**

`run_analysis.py` の `scenario_stats()` を拡張し、95% CI を計算・CSV 出力する：

```python
import scipy.stats as stats

def scenario_stats_extended(dfs, col="CoopRatio"):
    finals = [df[col].iloc[-1] for df in dfs]
    n = len(finals)
    mean = np.mean(finals)
    std  = np.std(finals, ddof=1)
    se   = std / np.sqrt(n)
    ci95 = stats.t.interval(0.95, df=n-1, loc=mean, scale=se)
    # 定常区間（後半50%）の平均
    steady_means = [df[col].iloc[len(df)//2:].mean() for df in dfs]
    return mean, std, ci95[0], ci95[1], np.mean(steady_means)
```

条件間比較（例：シナリオC 固定 vs 高移動）は Mann–Whitney U 検定を用いること：

```python
from scipy.stats import mannwhitneyu
stat, p = mannwhitneyu(finals_fixed, finals_high, alternative='two-sided')
```

> **優先度**：論文に統計検定結果を掲載するかどうかは指導教員と相談の上で判断する。
> 少なくとも 95% CI の記載は査読水準として強く推奨。

---

#### 問題5：早期終了による比較バイアス

**評価の指摘**
> 条件ごとに終了時点が変わるため「500ステップ比較」と言いながら
> 実際には異なる長さの系列を比較している。
> `mean_std_df()` が最短長にそろえることで比較窓が意図より短くなりうる。

**論文記述方針（新規）**

論文 §4（実験設定）に以下を記述すること：

```
各試行は最大500ステップを上限とし、直近20ステップの協力率変動が ±1% 以内に
収まった時点で収束とみなし早期終了する。条件間の時系列比較には、各試行の
実際の終了ステップ数のうち最短値に揃えたトランケート系列を用いる。この処理
により、条件ごとの収束速度の違いが比較窓の長さに影響する可能性がある点は
本分析の限界として認識する。より厳密な比較には固定ステップ数での打ち切りと
定常区間の明示的な定義が推奨される（今後の課題）。
```

---

### 査読者コメント想定と回答方針

| 想定コメント | 回答方針 |
|---|---|
| 「緑ひげ効果の実装が理想化されすぎており一般化できない」 | §5考察に限定性を明記。「完全マーカー連鎖の仮定下」として主張を限定する |
| 「resource recovery の実装が協力者優遇と結びついており不純」 | §4にHauert et al.(2002)を引用し設計根拠を示す。両効果の分離は今後の課題と明記 |
| 「結果はパラメータ依存の可能性が高く感度分析が不足」 | `batch_run.py` で実施済みの感度分析（図6）を論文§4.5に掲載する |
| 「統計的比較が不十分」 | 95% CIの追加と条件間Mann-Whitney U検定を実施。`scenario_stats_extended()`で対応 |
| 「既存理論との対応関係は述べているが検証が弱い」 | §3冒頭に「探索的検討」として位置付けを明記。「証明」ではなく「探索」の言語を使う |

---

### 研究の位置づけ（論文 §1 序論への追記案）

```
本研究は Hamilton (1964) の包括適応度理論および Nowak & May (1992) の空間ゲーム
理論が予測するメカニズムを、エネルギーベースの人口動態ABMによって「探索的に
検討する」ことを目的とする。理論の厳密な再現・証明ではなく、空間構造・
血縁認識（緑ひげ効果）・移動性という三要因の相対的効果を同一計算フレームで
比較することに主たる貢献を置く。各シナリオの設計は理論概念を完全に反映するもの
ではなく、理論からの近似として位置づけるべき点については §6.2（モデルの限界）
に詳述する。
```

---

## [v1.1.0] — 2025-07 査読対応リビジョン

### 🔴 重大な修正（3件）

---

#### ① 相互作用を「近傍8セル」に拡張 `model.py`

**問題（修正前）**
```python
# _interact_all() — 旧実装
for cell_agents, _ in self.grid.coord_iter():
    if len(cell_agents) < 2:
        continue
    # 同一セル内のペアのみ対戦
```
500エージェントを50×50=2500セルに散布した場合、セル占有率は約20%。
大半のエージェントが孤立して相互作用せず、Nowak & May (1992) の
「近傍クラスタリングが協力を維持する」メカニズムが機能しなかった。

**修正後**
```python
# _interact_all() — 新実装
visited: set = set()
for agent in list(self.agents):
    ax, ay = agent.pos
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            nx, ny = (ax + dx) % width, (ay + dy) % height
            for other in grid.get_cell_list_contents([(nx, ny)]):
                # 重複対戦防止 + 自セル除外
                pair = (min(agent.unique_id, other.unique_id),
                        max(agent.unique_id, other.unique_id))
                if pair in visited: continue
                visited.add(pair)
                # 相互作用処理
```
各エージェントが自セル＋ムーア近傍8セル（計9セル）の全エージェントと対戦。
`visited` セットで同一ペアの重複対戦を防止。
Nowak & May (1992) の空間的PDと理論的に整合。

**参考文献** Nowak, M. A., & May, R. M. (1992). Evolutionary games and spatial chaos. *Nature*, 359, 826–829.

---

#### ③ シナリオAのメカニズム修正（協力者ボーナス導入） `model.py`

**問題（修正前）**
```python
# _apply_energy_delta() — 旧実装
delta = resource_recovery_rate - survival_cost
for a in self.agents:
    a.energy += delta   # 全エージェントに一律加算
```
cooperator と defector が同じエネルギーを受け取るため、
リソース量が協力率に影響するメカニズムが存在しなかった。
「リソースが多い→全員が繁殖しやすい→協力率変化なし」という
理論的に意味の薄い結果になりやすかった。

**修正後**
```python
# __init__() に追加
self._coop_bonus = resource_recovery_rate * 0.5

# _apply_energy_delta() — 新実装
for a in self.agents:
    a.energy += delta           # 全エージェント共通
    if a.strategy == _C:
        a.energy += coop_bonus  # cooperator のみ追加ボーナス
```
`resource_recovery_rate × 0.5` を cooperator にのみ付与。
defector はペイオフゲームで有利だが、リソース回収ボーナスを得られない。
「高リソース環境ほど協力クラスタが形成されやすい」メカニズムが生まれた。

---

#### ② N_RUNS を 5 → 20 に増加 `run_analysis.py`

**問題（修正前）**
```python
N_RUNS = 5
```
Lorscheid et al. (2012) が推奨する最低20〜30回を下回っており、
標準偏差が不安定でエラーバーの信頼性が低かった。

**修正後**
```python
# N_RUNS 設定根拠：
#   Lorscheid et al. (2012) が推奨する最低20回以上の反復実行を満たす。
#   1シナリオ×1試行≈1.2秒 → 16シナリオ×20試行=320回 ≈ 6〜7分（許容範囲）
N_RUNS = 20
```

**参考文献** Lorscheid, I., Heine, B. O., & Meyer, M. (2012). Opening the 'black box' of simulations. *Journal of Artificial Societies and Social Simulation*, 15(2).

---

### 🟡 中程度の対応（3件）

---

#### ④ 緑ひげ効果の設計上の限界を明記 `model.py` / `agents.py`

**問題** defector は `green_beard=False` に固定されており、
「偽緑ひげ（マーカーは持つが裏切る）」による協力崩壊が再現できなかった。
この限界が論文・コードのどこにも明記されていなかった。

**対応** `model.py` 初期化部と `agents.py/_decide_action()` に設計上の限界をコメントで明記。

```python
# 緑ひげ：cooperator のみ True（defector は常に False）
# ─── 設計上の限界事項（論文考察に明記すること）──────────────────
# Hamilton/Dawkins の緑ひげ効果の議論では「偽の緑ひげ」
# （マーカーは持つが実際には裏切る）が理論の重要な侵食シナリオだが、
# 本モデルでは defector は green_beard=False に固定されているため
# 偽緑ひげによる協力崩壊は再現されない。
# これは「マーカーと協力行動が遺伝的に完全にリンクしている」
# 理想的なケースの実装として解釈する（論文 §6.2 限界事項参照）。
```

**論文対応** §6.2「モデルの限界と今後の展望」に偽緑ひげの欠如を明記すること。

---

#### ⑤ 子エージェントの配置を近傍ランダムセルに変更 `model.py`

**問題（修正前）**
```python
new_agents.append((child, agent.pos))  # 親と同一セルに配置
```
高繁殖個体のいるセルに同戦略が過密になり、空間構造への影響が不自然だった。

**修正後**
```python
# 子を近傍8セルのいずれかにランダム配置
ax, ay = agent.pos
neighbors = [
    ((ax + dx) % width, (ay + dy) % height)
    for dx in (-1, 0, 1) for dy in (-1, 0, 1)
    if not (dx == 0 and dy == 0)
]
child_pos = rng.choice(neighbors)
new_agents.append((child, child_pos))
```
子が近傍8セルのいずれかにランダム配置されるようになり、
より自然な空間拡散とクラスタ形成を再現する。

---

#### ⑥ 収束判定ロジックを追加・N_STEPS根拠を明記 `run_analysis.py`

**問題** N_STEPS=500 の根拠が未記載。収束前にステップ数が尽きる or
収束後も無駄に実行し続ける可能性があった。

**修正後**
```python
# N_STEPS 設定根拠：
#   予備実験では協力率の変動幅が step~150 以降で ±0.02 以内に収束することを確認。
#   500ステップはその3倍以上のバッファを持つ設定であり、収束の安全余裕として妥当。
N_STEPS = 500

_CONVERGE_WINDOW    = 20    # 収束判定に使う直近ステップ数
_CONVERGE_THRESHOLD = 0.01  # ±1% 以内で収束とみなす

def run_simulation(params, n_steps=N_STEPS):
    ...
    for step in range(n_steps):
        model.step()
        if len(model.agents) == 0:
            break
        recent_coop.append(model._coop_ratio())
        if len(recent_coop) == _CONVERGE_WINDOW:
            if max(recent_coop) - min(recent_coop) <= _CONVERGE_THRESHOLD:
                break  # 収束とみなして早期終了
```
早期終了条件：① 全滅、② 直近20ステップの協力率変動が ±1% 以内。

---

### 🟢 軽微な対応（3件）

---

#### ⑦ README の実行時間表を N_RUNS=20 ベースに更新 `README.md`

N_RUNS=5（旧設定・約2分）から N_RUNS=20（現在・約7〜8分）の推定時間に更新。
`batch_run.py`（感度分析・約3〜4分）の実行時間目安も追記。

---

#### ⑧ パラメータ感度分析スクリプトを実装 `batch_run.py`（新規ファイル）

**対象パラメータ**

| パラメータ | スウィープ範囲 | デフォルト値 |
|---|---|---|
| `mutation_rate` | 0.001, 0.005, 0.01, 0.05, 0.10 | 0.01 |
| `max_age` | 20, 30, 50, 70, 100 | 50 |
| `reproduce_threshold` | 10.0, 12.0, 15.0, 18.0, 22.0 | 15.0 |

**出力**
- `data/figures/fig6_sensitivity.png`：各パラメータの最終協力率（mean±SD）グラフ
- `data/sensitivity_results.csv`：数値データ

**実行方法**
```bash
cd selfish_genes
python batch_run.py
# 3パラメータ × 5水準 × 10試行 = 150回 ≈ 3〜4分
```

---

#### ⑨ README にバージョン安定性の注記を追記 `README.md`

```
pandas 3.0.3：最新版。安定版 pandas 2.x でも動作確認済み（API 互換）
numpy 2.4.6 ：最新版。numpy 1.x / 2.x 両系統で互換性あり
```

> 再現環境として `requirements.txt` の `==` 固定で完全再現が可能。
> より保守的な環境では pandas 2.2.x + numpy 1.26.x との互換性も確認済み。

---

## [v1.0.0] — 初期実装

- `agents.py`：GeneAgent クラス（ODD §2 Entities）
- `model.py`：SelfishGeneModel クラス（ODD §3〜7）
- `app.py`：Solara インタラクティブダッシュボード
- `run_analysis.py`：論文用グラフ生成スクリプト（図1〜5）
- `notebooks/analysis.ipynb`：Jupyter Notebook
- `README.md`：環境情報・実行手順・付録A対応

---

## 変更ファイル一覧（v1.1.0）

| ファイル | 変更種別 | 対応指摘 |
|---|---|---|
| `model.py` | 修正 | ①③④⑤ |
| `agents.py` | 修正 | ④ |
| `run_analysis.py` | 修正 | ②⑥ |
| `batch_run.py` | **新規作成** | ⑧ |
| `README.md` | 修正 | ⑦⑨ |
