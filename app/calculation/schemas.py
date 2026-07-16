"""命式計算エンジンの入出力スキーマ（Pydantic）。
Claude APIにはこの構造化データのみを渡し、干支・星等をLLMに推測させない。
"""
from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum

from pydantic import BaseModel, Field


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class BirthInput(BaseModel):
    birth_date: date
    birth_time: time | None = None
    birth_time_unknown: bool = False
    prefecture: str = ""
    city: str = ""
    gender: Gender = Gender.UNKNOWN


class PillarResult(BaseModel):
    stem: str
    branch: str
    stem_element: str
    branch_element: str
    stem_yinyang: str
    branch_yinyang: str
    hidden_stems: list[str] = Field(default_factory=list)
    ten_god: str | None = None  # 通変星（日干との関係。日柱自身はNone）
    twelve_stage: str | None = None  # 十二運


class FourPillarsResult(BaseModel):
    """四柱推命・陰陽五行側の構造化結果。"""

    year_pillar: PillarResult
    month_pillar: PillarResult
    day_pillar: PillarResult
    hour_pillar: PillarResult | None = None  # 出生時刻不明の場合はNone
    day_master_stem: str
    day_master_element: str
    day_master_yinyang: str
    five_element_balance: dict[str, int]
    hour_pillar_omitted_reason: str | None = None


class LuckCycleEntry(BaseModel):
    label: str  # 例: "1運目" や 西暦年
    start_date: date | None = None
    end_date: date | None = None
    stem: str
    branch: str
    ten_god: str | None = None
    twelve_stage: str | None = None
    note: str | None = None


class LuckCyclesResult(BaseModel):
    direction: str  # "順行" or "逆行" or "不明(性別未登録)"
    start_age_years: float | None = None
    start_date: date | None = None
    major_cycles: list[LuckCycleEntry] = Field(default_factory=list)  # 大運（四柱推命側）
    annual_cycles: list[LuckCycleEntry] = Field(default_factory=list)  # 年運
    monthly_cycles: list[LuckCycleEntry] = Field(default_factory=list)  # 月運
    unavailable_reason: str | None = None


class SanmeigakuResult(BaseModel):
    """算命学側の構造化結果。"""

    center_star: str | None = None
    center_star_confidence: str = "unverified"  # verified | provisional | unverified
    juudai_shusei: dict[str, str] = Field(default_factory=dict)  # 位置(年干/月干/時干/年支/月支/日支/時支) -> 十大主星
    juuni_daijuusei: dict[str, str] = Field(default_factory=dict)  # 位置(年支/月支/日支/時支) -> 十二大従星
    tenchuusatsu: list[str] = Field(default_factory=list)
    guardian_deity: str | None = None
    guardian_deity_confidence: str = "unverified"
    isouhou_note: str | None = None
    isouhou_confidence: str = "unverified"
    major_cycles: list[LuckCycleEntry] = Field(default_factory=list)  # 大運（算命学側、四柱推命側と別保持）


class CalculationMetadata(BaseModel):
    policy_version: str
    calculated_at: datetime
    input_echo: BirthInput
    birth_time_known: bool
    accuracy_notes: list[str] = Field(default_factory=list)


class CalculationResult(BaseModel):
    """四柱推命側・算命学側を別データとして保持する統合結果。
    どちらか一方を勝手に上書きしない。
    """

    shichuu_suimei: FourPillarsResult
    sanmeigaku: SanmeigakuResult
    luck_cycles: LuckCyclesResult
    metadata: CalculationMetadata
