"""
model.py — SelfishGeneModel の定義
ODDプロトコル対応：Process Overview, Initialization, Submodels

空間的囚人のジレンマ（Spatial Prisoner's Dilemma）モデル。
エージェントが2次元グリッド上を移動しながら相互作用し、
繁殖・死滅を通じて「利己的遺伝子 vs 利他的遺伝子」の淘汰を再現する。

ペイオフ行列（囚人のジレンマ）：
    T > R > P > S を満たすことが必須条件
    CC: R=3  CD: S=0  DC: T=5  DD: P=1

相互作用設計（Nowak & May 1992 準拠）：
    各エージェントは自セルおよびムーア近傍8セルの全エージェントと対戦する。
    これにより「近傍クラスタリングが協力を維持する」という空間的PDの本質的
    メカニズムが機能する。同一ペアの重複対戦は発生しないようにIDで制御する。

シナリオAのメカニズム（リソースと協力の関係）：
    resource_recovery_rate : 全エージェントへの基礎エネルギー回復（環境リソース量）。
    coop_bonus_rate        : cooperator のみが受け取る追加ボーナス（公共財効果の強さ）。
    この2パラメータを独立させることで「環境リソース量の効果」と
    「協力者優遇の強さの効果」を別々に操作できる（v1.3.0 分離）。
    シナリオAではどちらか一方を変化させ、もう一方をデフォルト固定とする。
"""

import mesa
import numpy as np
from agents import GeneAgent

_C = GeneAgent.COOPERATOR  # 0
_D = GeneAgent.DEFECTOR    # 1

# ==========================================================================
# ペイオフ定数（2×2タプル。辞書ルックアップ不要）
# payoff[act_self][act_other]  act: 0=C, 1=D
# CC=3, CD=0, DC=5, DD=1
# ==========================================================================
_PAYOFF = (
    (3.0, 0.0),   # C vs C=3, C vs D=0
    (5.0, 1.0),   # D vs C=5, D vs D=1
)

# ==========================================================================
# ベースケースのデフォルトパラメータ（論文 §4.1 に対応）
# ==========================================================================

DEFAULT_PARAMS = {
    "width": 50,
    "height": 50,
    "n_agents": 500,
    "initial_coop_ratio": 0.5,
    "diffusion_rate": 0.1,
    "mutation_rate": 0.01,
    "resource_recovery_rate": 1.0,
    # coop_bonus_rate：cooperator のみが受け取る公共財ボーナスの強さ。
    # resource_recovery_rate から分離（v1.3.0）することで、
    # シナリオAで「環境リソース量」と「協力者優遇」を独立操作できる。
    "coop_bonus_rate": 0.5,
    "green_beard_enabled": False,
    "recognition_error_rate": 0.0,
    "initial_energy": 10.0,
    "survival_cost": 0.5,
    "reproduce_threshold": 15.0,
    "reproduce_cost": 8.0,
    "max_age": 50,
    "max_agents": 2000,   # 個体数の上限（これを超えると繁殖しない）
    "seed": 42,
}

# ==========================================================================
# シナリオ定義（論文 §4.2〜4.4 に対応）
# ==========================================================================

# シナリオA：リソース豊富 vs 枯渇環境
#   resource_recovery_rate のみを変化させ coop_bonus_rate は固定（環境リソース量の純粋操作）
SCENARIO_A_RICH = {**DEFAULT_PARAMS, "resource_recovery_rate": 3.0}
SCENARIO_A_POOR = {**DEFAULT_PARAMS, "resource_recovery_rate": 0.2}

# シナリオA別軸：公共財ボーナスの強さの操作（resource_recovery_rate は固定）
SCENARIO_A_BONUS_HIGH = {**DEFAULT_PARAMS, "coop_bonus_rate": 1.5}
SCENARIO_A_BONUS_LOW  = {**DEFAULT_PARAMS, "coop_bonus_rate": 0.1}

# シナリオB：緑ひげ効果（認識誤り率 ε の検証）
SCENARIO_B_PERFECT = {**DEFAULT_PARAMS, "green_beard_enabled": True,  "recognition_error_rate": 0.0}
SCENARIO_B_ERROR05 = {**DEFAULT_PARAMS, "green_beard_enabled": True,  "recognition_error_rate": 0.05}
SCENARIO_B_ERROR10 = {**DEFAULT_PARAMS, "green_beard_enabled": True,  "recognition_error_rate": 0.10}
SCENARIO_B_ERROR20 = {**DEFAULT_PARAMS, "green_beard_enabled": True,  "recognition_error_rate": 0.20}
SCENARIO_B_NONE    = {**DEFAULT_PARAMS, "green_beard_enabled": False, "recognition_error_rate": 0.0}

# シナリオC：移動性と局所協力関係
SCENARIO_C_FIXED  = {**DEFAULT_PARAMS, "diffusion_rate": 0.0}
SCENARIO_C_LOW    = {**DEFAULT_PARAMS, "diffusion_rate": 0.1}
SCENARIO_C_MID    = {**DEFAULT_PARAMS, "diffusion_rate": 0.3}
SCENARIO_C_HIGH   = {**DEFAULT_PARAMS, "diffusion_rate": 0.9}


# ==========================================================================
# メインモデルクラス
# ==========================================================================

class SelfishGeneModel(mesa.Model):
    """
    利己的な遺伝子シミュレーション — メインモデル。

    ODD Process Overview (§3)：
        各ステップで以下を順番に実行する：
        1. 全エージェントがランダム順で step()（移動 + 老化）を実行
        2. セル単位バッチで囚人のジレンマ相互作用を処理
        3. エネルギーが繁殖閾値を超えたエージェントが繁殖（突然変異あり）
        4. エネルギーがゼロ以下または最大年齢超過のエージェントが死滅
        5. リソース回復・生存コスト・キャッシュ集計・MeanEnergy を1ループで処理
        6. DataCollector がデータを記録する

    ODD Initialization (§5)：
        グリッドをランダムに初期化し、
        initial_coop_ratio の比率で cooperator / defector を配置する。

    ODD Submodels (§7)：
        _interact_all()       : セル単位バッチ相互作用（最適化済み）
        _reproduce_and_die()  : 繁殖＋死滅サブモデル（突然変異含む）
        _apply_energy_delta() : エネルギー差分適用 + キャッシュ更新を1ループで統合
        payoff_matrix         : 囚人のジレンマのペイオフ
    """

    def __init__(
        self,
        width: int = DEFAULT_PARAMS["width"],
        height: int = DEFAULT_PARAMS["height"],
        n_agents: int = DEFAULT_PARAMS["n_agents"],
        initial_coop_ratio: float = DEFAULT_PARAMS["initial_coop_ratio"],
        diffusion_rate: float = DEFAULT_PARAMS["diffusion_rate"],
        mutation_rate: float = DEFAULT_PARAMS["mutation_rate"],
        resource_recovery_rate: float = DEFAULT_PARAMS["resource_recovery_rate"],
        coop_bonus_rate: float = DEFAULT_PARAMS["coop_bonus_rate"],
        green_beard_enabled: bool = DEFAULT_PARAMS["green_beard_enabled"],
        recognition_error_rate: float = DEFAULT_PARAMS["recognition_error_rate"],
        initial_energy: float = DEFAULT_PARAMS["initial_energy"],
        survival_cost: float = DEFAULT_PARAMS["survival_cost"],
        reproduce_threshold: float = DEFAULT_PARAMS["reproduce_threshold"],
        reproduce_cost: float = DEFAULT_PARAMS["reproduce_cost"],
        max_age: int = DEFAULT_PARAMS["max_age"],
        max_agents: int = DEFAULT_PARAMS["max_agents"],
        seed: int = DEFAULT_PARAMS["seed"],
    ) -> None:
        super().__init__(rng=seed)

        # パラメータの保持
        self.width = width
        self.height = height
        self.n_agents = n_agents
        self.initial_coop_ratio = initial_coop_ratio
        self.diffusion_rate = diffusion_rate
        self.mutation_rate = mutation_rate
        self.resource_recovery_rate = resource_recovery_rate
        self.coop_bonus_rate = coop_bonus_rate
        self.green_beard_enabled = green_beard_enabled
        self.recognition_error_rate = recognition_error_rate
        self.initial_energy = initial_energy
        self.survival_cost = survival_cost
        self.reproduce_threshold = reproduce_threshold
        self.reproduce_cost = reproduce_cost
        self.max_age = max_age
        self.max_agents = max_agents

        # 基礎エネルギー差分（全エージェント共通）= リソース回復 - 生存コスト
        self._net_energy_delta = resource_recovery_rate - survival_cost
        # 協力者ボーナス（シナリオA用）：
        #   coop_bonus_rate は resource_recovery_rate から独立したパラメータ（v1.3.0）。
        #   cooperator のみが受け取る追加エネルギー = coop_bonus_rate。
        #   これにより「環境リソース量の効果」と「協力者優遇の効果」を分離して操作できる。
        self._coop_bonus = coop_bonus_rate

        # ------------------------------------------------------------------
        # ODD Submodel：ペイオフ行列（囚人のジレンマ）
        # T=5 > R=3 > P=1 > S=0 を満たす標準設定
        # ------------------------------------------------------------------
        self.payoff_matrix = {
            "C": {"C": 3.0, "D": 0.0},   # CC=R=3, CD=S=0
            "D": {"C": 5.0, "D": 1.0},   # DC=T=5, DD=P=1
        }

        # グリッドの初期化（MultiGrid：1セルに複数エージェント可）
        self.grid = mesa.space.MultiGrid(width, height, torus=True)

        # DataCollector の設定
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Cooperators":     lambda m: m._cached_coop,
                "Defectors":       lambda m: m._cached_defect,
                "CoopRatio":       lambda m: m._cached_coop_ratio,
                "TotalAgents":     lambda m: m._cached_total,
                "MeanEnergy":      lambda m: m._cached_mean_energy,
            }
        )

        # キャッシュ初期化
        self._cached_coop        = 0
        self._cached_defect      = 0
        self._cached_total       = 0
        self._cached_coop_ratio  = 0.0
        self._cached_mean_energy = 0.0

        # ------------------------------------------------------------------
        # ODD Initialization (§5)：エージェントの初期配置
        # ------------------------------------------------------------------
        for _ in range(n_agents):
            strategy = (
                _C if self.random.random() < initial_coop_ratio else _D
            )
            # 緑ひげ：cooperator のみ True（defector は常に False）
            # ─── 設計上の限界事項（論文考察に明記すること）───────────────────
            # Hamilton/Dawkins の緑ひげ効果の議論では「偽の緑ひげ」
            # （マーカーは持つが実際には裏切る）が理論の重要な侵食シナリオだが、
            # 本モデルでは defector は green_beard=False に固定されているため
            # 偽緑ひげによる協力崩壊は再現されない。
            # これは「マーカーと協力行動が遺伝的に完全にリンクしている」
            # 理想的なケースの実装として解釈する（論文 §6.2 限界事項参照）。
            # ──────────────────────────────────────────────────────────────────
            gb = (strategy == _C) and green_beard_enabled

            agent = GeneAgent(
                model=self,
                strategy=strategy,
                energy=initial_energy,
                green_beard=gb,
            )
            # ランダムな空きセルに配置
            x = self.random.randrange(width)
            y = self.random.randrange(height)
            self.grid.place_agent(agent, (x, y))

        # キャッシュを更新してから初期データを収集
        # （_apply_energy_delta と統合済みのため初期化時だけ直接計算）
        coop = sum(1 for a in self.agents if a.strategy == _C)
        total = len(self.agents)
        self._cached_coop        = coop
        self._cached_defect      = total - coop
        self._cached_total       = total
        self._cached_coop_ratio  = coop / total if total > 0 else 0.0
        self._cached_mean_energy = (
            sum(a.energy for a in self.agents) / total if total > 0 else 0.0
        )
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    # ODD Process Overview：メインステップ
    # ------------------------------------------------------------------

    def step(self) -> None:
        """1ステップの全処理フロー。"""
        # 1. 全エージェントがランダム順で移動・老化
        self.agents.shuffle_do("step")
        # 2. セル単位バッチで相互作用（最大の最適化ポイント）
        self._interact_all()
        # 3. 繁殖 + 死滅を1パスで処理
        self._reproduce_and_die()
        # 4. 生存コスト消費 + リソース回復 + キャッシュ更新を1パスで適用
        self._apply_energy_delta()
        # 5. データ収集（キャッシュは _apply_energy_delta 内で更新済み）
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    # 相互作用バッチ処理（最適化：セル単位で1回だけ走査）
    # ------------------------------------------------------------------

    def _interact_all(self) -> None:
        """
        Nowak & May (1992) 準拠の近傍相互作用バッチ処理。

        各エージェントは自セル＋ムーア近傍8セル（計9セル）に存在する
        全エージェントと囚人のジレンマを行う。
        同一ペアが重複対戦しないよう、処理済みペアを visited セットで管理。

        設計根拠：
            500エージェントを50×50=2500セルに散布した場合、
            同一セル内の衝突確率は低い。近傍相互作用にすることで
            「協力クラスタが形成され空間的に安定する」という
            空間的PDの本質的メカニズムを再現できる（Nowak & May 1992）。

        ペイオフは2×2タプル _PAYOFF で直接参照（辞書ルックアップ不要）。
        strategy は整数（0=C, 1=D）のため比較コストが最小。
        """
        payoff = _PAYOFF
        grid   = self.grid
        width  = self.width
        height = self.height
        visited: set = set()   # 処理済みペア (min_id, max_id)

        for agent in list(self.agents):
            ax, ay = agent.pos
            # 自セル＋ムーア近傍8セルを直接列挙
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = (ax + dx) % width, (ay + dy) % height
                    for other in grid.get_cell_list_contents([(nx, ny)]):
                        if other is agent:
                            continue
                        # 重複対戦を防ぐ
                        pair = (min(agent.unique_id, other.unique_id),
                                max(agent.unique_id, other.unique_id))
                        if pair in visited:
                            continue
                        visited.add(pair)
                        act_a = agent._decide_action(other)
                        act_b = other._decide_action(agent)
                        agent.energy += payoff[act_a][act_b]
                        other.energy += payoff[act_b][act_a]

    # ------------------------------------------------------------------
    # ODD Submodel：繁殖 + 死滅を1パスで処理
    # ------------------------------------------------------------------

    def _reproduce_and_die(self) -> None:
        """
        繁殖と死滅を1ループで処理。

        繁殖ルール：
        - 親のエネルギーから reproduce_cost を消費
        - 子は親と同じ strategy を継承（突然変異なしの場合）
        - mutation_rate の確率で strategy が反転する（突然変異）
        - 子は親のムーア近傍8セルからランダムに選んだセルに配置（指摘⑤への対応）
          これにより「同戦略が過密になる」問題を緩和し、より自然な空間拡散を再現する。
          （従来は親と同一セルに配置していたため、高繁殖個体のいるセルが過密になっていた）
        """
        reproduce_threshold = self.reproduce_threshold
        reproduce_cost      = self.reproduce_cost
        mutation_rate       = self.mutation_rate
        max_age             = self.max_age
        initial_energy      = self.initial_energy
        green_beard_enabled = self.green_beard_enabled
        rng                 = self.random
        width               = self.width
        height              = self.height

        new_agents  = []
        dead_agents = []

        current_total = len(self.agents)
        max_agents    = self.max_agents

        for agent in list(self.agents):
            # 繁殖チェック（上限を超えていたら繁殖しない）
            if agent.energy >= reproduce_threshold and current_total < max_agents:
                agent.energy -= reproduce_cost
                current_total += 1

                if rng.random() < mutation_rate:
                    child_strategy = _D if agent.strategy == _C else _C
                else:
                    child_strategy = agent.strategy

                child_gb = (child_strategy == _C) and green_beard_enabled
                child = GeneAgent(
                    model=self,
                    strategy=child_strategy,
                    energy=initial_energy,
                    green_beard=child_gb,
                )
                # 子を近傍8セルのいずれかにランダム配置
                ax, ay = agent.pos
                neighbors = [
                    ((ax + dx) % width, (ay + dy) % height)
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if not (dx == 0 and dy == 0)
                ]
                child_pos = rng.choice(neighbors)
                new_agents.append((child, child_pos))

            # 死滅チェック
            if agent.energy <= 0 or agent.age >= max_age:
                dead_agents.append(agent)

        # まとめて配置・除去（ループ中の構造変更を避ける）
        for child, pos in new_agents:
            self.grid.place_agent(child, pos)

        for agent in dead_agents:
            self.grid.remove_agent(agent)
            agent.remove()

    # ------------------------------------------------------------------
    # 生存コスト消費 + リソース回復 + 協力者ボーナス + キャッシュ更新を1パスで統合
    # ------------------------------------------------------------------

    def _apply_energy_delta(self) -> None:
        """
        生存コスト・リソース回復・協力者ボーナス・キャッシュ・MeanEnergy を1ループで処理。

        シナリオAのメカニズム（v1.3.0 でパラメータを独立化）：
            全エージェントに共通の基礎差分（resource_recovery_rate - survival_cost）
            を加算した上で、cooperator にのみ追加ボーナスを付与する。
            ボーナス = coop_bonus_rate（resource_recovery_rate とは独立した変数）。
            これにより「環境リソース量の効果」と「協力者優遇の効果」を
            別々に操作できる Factorial 設計が可能になった。
            defector はペイオフゲームで有利だが、公共財ボーナスを得られない。
        """
        delta      = self._net_energy_delta
        coop_bonus = self._coop_bonus
        coop       = 0
        energy_sum = 0.0
        for a in self.agents:
            a.energy += delta
            if a.strategy == _C:
                a.energy += coop_bonus
                coop += 1
            energy_sum += a.energy
        total = len(self.agents)
        self._cached_coop        = coop
        self._cached_defect      = total - coop
        self._cached_total       = total
        self._cached_coop_ratio  = coop / total if total > 0 else 0.0
        self._cached_mean_energy = energy_sum / total if total > 0 else 0.0

    def _update_cache(self) -> None:
        """後方互換のため残す。_apply_energy_delta が兼ねるため通常は呼ばれない。"""
        pass

    # ------------------------------------------------------------------
    # DataCollector 用ヘルパーメソッド（キャッシュ経由）
    # ------------------------------------------------------------------

    def _count_strategy(self, strategy: int) -> int:
        if strategy == _C:
            return self._cached_coop
        return self._cached_defect

    def _coop_ratio(self) -> float:
        return self._cached_coop_ratio

    # ------------------------------------------------------------------
    # グリッドスナップショット（可視化・分析用）
    # ------------------------------------------------------------------

    def get_grid_snapshot(self) -> np.ndarray:
        """
        グリッドの状態を numpy 配列で返す。
        0 = 空, 1 = cooperator, 2 = defector
        論文図5（空間スナップショット）の生成に使用。

        最適化：エージェントのリストを直接走査する方式。
        エージェント数 << グリッドセル数（500 << 2500）のため高速。
        """
        coop_count   = np.zeros((self.width, self.height), dtype=np.int16)
        defect_count = np.zeros((self.width, self.height), dtype=np.int16)

        for agent in self.agents:
            x, y = agent.pos
            if agent.strategy == _C:
                coop_count[x, y] += 1
            else:
                defect_count[x, y] += 1

        snapshot = np.zeros((self.width, self.height), dtype=np.int8)
        occupied = (coop_count + defect_count) > 0
        snapshot[occupied & (coop_count >= defect_count)] = 1
        snapshot[occupied & (defect_count > coop_count)]  = 2

        return snapshot
