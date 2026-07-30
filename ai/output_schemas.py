"""Claude最終出力の構造化スキーマ。事実・命式上の傾向・AI仮説・確認事項・提案を
明確なラベルで分離する（要件7章「事実、占術上の解釈、AIの推測を明確に分ける」）。
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Label(str, Enum):
    FACT = "登録されている事実"
    FORTUNE_TRAIT = "命式上の傾向"
    AI_HYPOTHESIS = "AIによる人事仮説"
    CONFIRM = "確認したいこと"
    PROPOSAL = "提案"


class LabeledPoint(BaseModel):
    label: Label
    text: str


class SimpleAnalysisResponse(BaseModel):
    person_id: str
    conclusion: str
    essence: str
    strengths: list[LabeledPoint] = Field(
        default_factory=list,
        description=(
            "この人物の強み・長所。命式・大運等の裏付けがあるものを具体的に、"
            "必ず1件以上含めてください。"
        ),
    )
    cautions: list[LabeledPoint] = Field(
        default_factory=list,
        description=(
            "この人物の注意点・弱み。命式・大運等から明確に読み取れる場合のみ記載してください。"
            "際立った注意点の兆候が無い場合は、無理に作り出さず空のリストのままにしてください。"
        ),
    )
    current_approach: list[LabeledPoint] = Field(default_factory=list)
    fortune_basis: list[str] = Field(default_factory=list)
    accuracy_notes: list[str] = Field(default_factory=list)


class TeamCandidate(BaseModel):
    name: str
    reason: str  # 命式・MBTI等に基づく推薦理由（AIによる仮説であることが前提）


class TeamRecommendationResponse(BaseModel):
    """新プロジェクトメンバー等の候補推薦結果。
    要件24章の通り、占術だけで採用・配置を自動決定しないための注意書きを
    必ずcaveatに含める。"""

    criteria: str
    recommended: list[TeamCandidate] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class DetailedAnalysisResponse(BaseModel):
    person_id: str
    conclusion: str
    fortune_basis: list[str] = Field(default_factory=list)
    essence: str
    strengths: list[LabeledPoint] = Field(
        default_factory=list,
        description=(
            "この人物の強み。命式・大運・年運等の裏付けがあるものを具体的に、"
            "必ず1件以上、可能であれば2〜4件含めてください。"
        ),
    )
    weaknesses: list[LabeledPoint] = Field(
        default_factory=list,
        description=(
            "この人物の弱み・注意点。命式・大運等から明確に読み取れる場合のみ記載してください。"
            "大運・年運・十二運などに際立った弱みの兆候が見当たらない場合は、"
            "無理に弱みを作り出さず、空のリストのままにしてください。"
        ),
    )
    growth_guidance: list[LabeledPoint] = Field(
        default_factory=list,
        description=(
            "この人物の伸ばし方・成長を後押しする具体的な関わり方。強みや「伸びどき」"
            "（十二運が長生・冠帯・建禄・帝旺にあたる大運・年運など）を踏まえ、"
            "どのように任せる・関わると伸びやすいかを具体的に、可能であれば1〜3件含めてください。"
        ),
    )
    suitable_roles: list[LabeledPoint] = Field(default_factory=list)
    current_major_luck: str = ""
    current_annual_luck: str = ""
    monthly_luck: str | None = None
    approach_and_communication: list[LabeledPoint] = Field(default_factory=list)
    interview_questions: list[str] = Field(default_factory=list)
    hr_proposals: list[LabeledPoint] = Field(default_factory=list)
    facts_to_confirm: list[str] = Field(default_factory=list)
    accuracy_notes: list[str] = Field(default_factory=list)


class CompatibilityAnalysisResponse(BaseModel):
    """二者間の「相性チェック」結果。十干（日主）だけでなく、四柱推命の命式全体
    （年柱・月柱・日柱・時柱）と算命学（十二運・通変星・天中殺/空亡）を踏まえて
    解釈することを前提にしたスキーマ。"""

    person_a_id: str
    person_b_id: str
    person_a_name: str
    person_b_name: str
    conclusion: str
    fortune_basis: list[str] = Field(default_factory=list)
    good_points: list[LabeledPoint] = Field(
        default_factory=list,
        description=(
            "二人の相性が良いとされる点。日干同士の五行の関係（比和・相生等）、"
            "年柱・月柱・日柱・時柱の干支の組み合わせ、通変星、大運・年運の重なりなど、"
            "命式全体を踏まえた具体的な根拠とともに必ず1件以上含めてください。"
        ),
    )
    friction_points: list[LabeledPoint] = Field(
        default_factory=list,
        description=(
            "衝突・すれ違いが起きやすいとされる点。命式の関係性から明確に読み取れる"
            "場合のみ記載してください。際立った根拠が無い場合は、無理に作り出さず"
            "空のリストのままにしてください。"
        ),
    )
    communication_tips: list[LabeledPoint] = Field(
        default_factory=list,
        description="この二人がうまく関わるための具体的なコミュニケーションの工夫・接し方。",
    )
    accuracy_notes: list[str] = Field(default_factory=list)
