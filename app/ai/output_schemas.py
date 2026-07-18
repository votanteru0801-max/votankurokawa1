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
    strengths: list[LabeledPoint] = Field(default_factory=list)
    cautions: list[LabeledPoint] = Field(default_factory=list)
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
    strengths: list[LabeledPoint] = Field(default_factory=list)
    weaknesses: list[LabeledPoint] = Field(default_factory=list)
    suitable_roles: list[LabeledPoint] = Field(default_factory=list)
    current_major_luck: str = ""
    current_annual_luck: str = ""
    monthly_luck: str | None = None
    approach_and_communication: list[LabeledPoint] = Field(default_factory=list)
    interview_questions: list[str] = Field(default_factory=list)
    hr_proposals: list[LabeledPoint] = Field(default_factory=list)
    facts_to_confirm: list[str] = Field(default_factory=list)
    accuracy_notes: list[str] = Field(default_factory=list)
