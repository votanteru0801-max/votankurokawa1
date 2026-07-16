"""計算ポリシー。流派・サイトによって結果が変わりうる項目をハードコードせず、
設定として切り替えられるようにする。既定値は docs/calculation-policy.md を参照。
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class YearPillarBoundary(str, Enum):
    RISSHUN = "risshun"       # 立春基準（既定）
    JAN1 = "jan1"              # 西暦1月1日基準


class CenterStarMethod(str, Enum):
    MONTH_BRANCH_MAIN_QI = "month_branch_main_qi"  # 月支の蔵干(本気)から算出（既定）
    DAY_BRANCH_MAIN_QI = "day_branch_main_qi"        # 日支の蔵干(本気)から算出（代替流派）


class GuardianDeityMethod(str, Enum):
    BALANCE_WEAKEST_ELEMENT = "balance_weakest_element"  # 五行バランスで最弱の五行を補う（簡易版・既定）


class LuckStartAgeMethod(str, Enum):
    DAYS_DIV_3 = "days_div_3"  # 節入りまでの日数 ÷ 3 = 年（余りは月換算）（既定）


class CalculationPolicy(BaseModel):
    """命式計算の挙動を決める設定値。"""

    version: str = "2026.1"

    # 年柱切替基準
    year_pillar_boundary: YearPillarBoundary = YearPillarBoundary.RISSHUN

    # 月柱に使う節入り（現状は二十四節気のうち「節」固定。将来「中気」流派に対応する余地を残す）
    month_boundary_uses_setsu: bool = True

    # 日付変更時刻（0時 or 23時）
    day_boundary_hour: int = Field(default=0, ge=0, le=23)

    # 出生時刻の補正（経度差補正・均時差補正等）の有無
    true_solar_time_correction: bool = False

    # 大運の順行・逆行判定（性別 × 年干の陰陽。標準方式のみ実装）
    # 陽男陰女=順行、陰男陽女=逆行
    # 算命学の中心星算出方法
    center_star_method: CenterStarMethod = CenterStarMethod.MONTH_BRANCH_MAIN_QI

    # 守護神判定方法
    guardian_deity_method: GuardianDeityMethod = GuardianDeityMethod.BALANCE_WEAKEST_ELEMENT

    # 大運開始年齢の算出方法
    luck_start_age_method: LuckStartAgeMethod = LuckStartAgeMethod.DAYS_DIV_3

    class Config:
        frozen = True


DEFAULT_POLICY = CalculationPolicy()
