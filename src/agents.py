"""
agents.py — GeneAgent の定義
ODDプロトコル対応：Entities, State Variables, Design Concepts

各エージェントは「遺伝子を持つ個体」を表す。
戦略（cooperator / defector）が遺伝子座に対応し、
エネルギー・年齢・繁殖・死滅ルールで自然選択をシミュレートする。
"""

import mesa


class GeneAgent(mesa.Agent):
    """
    利己的な遺伝子シミュレーションのエージェント。

    State Variables (ODD §2):
        strategy (int)        : COOPERATOR=0 | DEFECTOR=1 — 遺伝子戦略
        energy (float)        : 現在のエネルギー（適応度の代理変数）
        age (int)             : 現在の年齢（ステップ数）
        green_beard (bool)    : 血縁認識マーカー（シナリオB用）

    Design Concepts (ODD §4):
        Fitness      : energy が繁殖・生存の確率を決定する
        Inheritance  : 親の strategy を子が引き継ぎ、mutation_rate で突然変異
        Stochasticity: 移動・突然変異・繁殖確率にランダム性が入る
        Emergence    : 協力率は個体ルールから創発する（直接設定しない）
    """

    COOPERATOR = 0
    DEFECTOR   = 1

    __slots__ = ("strategy", "energy", "age", "green_beard")

    def __init__(
        self,
        model: mesa.Model,
        strategy: int = 0,
        energy: float = 10.0,
        green_beard: bool = False,
    ) -> None:
        super().__init__(model)
        self.strategy: int = strategy   # 0=cooperator, 1=defector
        self.energy: float = energy
        self.age: int = 0
        self.green_beard: bool = green_beard

    # ------------------------------------------------------------------
    # 主行動ステップ（model.step() から呼ばれる）
    # 相互作用はモデル側でセル単位バッチ処理するためここでは移動のみ。
    # ------------------------------------------------------------------

    def step(self) -> None:
        """1ステップの行動：移動 → 老化。エネルギー変動は model 側で一括処理。"""
        self._move()
        self.age += 1

    # ------------------------------------------------------------------
    # 移動（シナリオC：diffusion_rate で制御）
    # ------------------------------------------------------------------

    def _move(self) -> None:
        """diffusion_rate の確率でランダムな隣接セルに移動する。
        トーラスグリッド上のムーア近傍は常に8セル固定のため直接計算する。
        """
        if self.model.random.random() < self.model.diffusion_rate:
            x, y = self.pos
            w = self.model.width
            h = self.model.height
            # 8近傍を直接列挙（get_neighborhood() 呼び出しを省略）
            neighbors = (
                ((x - 1) % w, (y - 1) % h),
                ((x - 1) % w,  y),
                ((x - 1) % w, (y + 1) % h),
                ( x,          (y - 1) % h),
                ( x,          (y + 1) % h),
                ((x + 1) % w, (y - 1) % h),
                ((x + 1) % w,  y),
                ((x + 1) % w, (y + 1) % h),
            )
            new_pos = self.model.random.choice(neighbors)
            self.model.grid.move_agent(self, new_pos)

    # ------------------------------------------------------------------
    # 行動決定（モデル側バッチ処理から呼ばれる）
    # ------------------------------------------------------------------

    def _decide_action(self, other: "GeneAgent") -> int:
        """
        相手に対する行動（0=C, 1=D）を決定する。

        通常モード  : 自身の strategy をそのまま返す。
        緑ひげモード: マーカーの一致・不一致と認識誤り率で決定。

        設計上の限界（ODD §4 Design Concepts / 論文考察 §6.2）：
            本実装は「協力遺伝子とマーカー遺伝子が完全にリンクしている」
            理想的なシナリオを再現する。defector は green_beard=False に
            固定されているため、「偽緑ひげ（マーカーを持つが裏切る）」
            による協力の侵食（Dawkins 1976 の cheating green beard）は
            本モデルでは観察されない点に注意が必要。
        """
        if self.model.green_beard_enabled:
            # self.green_beard AND other.green_beard がともに True の場合のみ
            # 「同マーカー保持者」とみなす。
            # （旧実装の == では defector 同士（False==False）も True になるバグがあった）
            shares_marker = self.green_beard and other.green_beard
            if self.model.random.random() >= self.model.recognition_error_rate:
                # 正しく認識：同マーカーなら協力
                return GeneAgent.COOPERATOR if shares_marker else GeneAgent.DEFECTOR
            else:
                # 誤認識：逆転
                return GeneAgent.DEFECTOR if shares_marker else GeneAgent.COOPERATOR
        return self.strategy
