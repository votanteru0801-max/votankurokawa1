"""大運・年運・月運の決定論的計算。四柱推命側の大運/年運/月運を扱う。
算命学側の大運は sanmeigaku.py 側のデータと別保持する方針のため、
本モジュールの結果は FourPillarsResult を基準に計算する（四柱推命基準）。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.calculation import solar_terms
from app.calculation.four_pillars import (
    compute_ten_god,
    twelve_stage_for,
    year_and_month_ganzhi_for,
)
from app.calculation.policy import CalculationPolicy
from app.calculation.schemas import BirthInput, FourPillarsResult, Gender, LuckCycleEntry, LuckCyclesResult
from app.calculation.tables import BRANCHES, STEM_YINYANG, STEMS, ganzhi_index

JST = ZoneInfo("Asia/Tokyo")
DAYS_PER_YEAR = 3.0  # 大運開始年齢の換算(3日=1年)。docs/calculation-policy.md 参照


def _add_years(d: date, years: float) -> date:
    return d + timedelta(days=years * 365.2425)


def calculate_major_cycles(
    birth: BirthInput,
    four_pillars: FourPillarsResult,
    policy: CalculationPolicy,
    num_cycles: int = 8,
) -> LuckCyclesResult:
    if birth.gender not in (Gender.MALE, Gender.FEMALE):
        return LuckCyclesResult(
            direction="不明(性別未登録)",
            unavailable_reason="性別が未登録、または男性・女性以外のため大運の順行・逆行を判定できません。",
        )

    representative_time = birth.birth_time or datetime.min.time().replace(hour=12)
    birth_dt = datetime.combine(birth.birth_date, representative_time, tzinfo=JST)

    year_yinyang = STEM_YINYANG[four_pillars.year_pillar.stem]
    forward = (birth.gender == Gender.MALE and year_yinyang == "陽") or (
        birth.gender == Gender.FEMALE and year_yinyang == "陰"
    )
    direction = "順行" if forward else "逆行"

    boundaries = solar_terms.month_term_boundaries_around(birth_dt)
    if forward:
        candidates = [e for e in boundaries if e[1] > birth_dt]
        target_dt = candidates[0][1]
        days = (target_dt - birth_dt).total_seconds() / 86400
    else:
        candidates = [e for e in boundaries if e[1] <= birth_dt]
        target_dt = candidates[-1][1]
        days = (birth_dt - target_dt).total_seconds() / 86400

    start_age_years = days / DAYS_PER_YEAR
    start_date = _add_years(birth.birth_date, start_age_years)

    day_stem = four_pillars.day_master_stem
    month_index60 = ganzhi_index(four_pillars.month_pillar.stem, four_pillars.month_pillar.branch)

    cycles: list[LuckCycleEntry] = []
    for i in range(num_cycles):
        step = i + 1
        idx = (month_index60 + step) % 60 if forward else (month_index60 - step) % 60
        stem, branch = STEMS[idx % 10], BRANCHES[idx % 12]
        cycle_start_age = start_age_years + 10 * i
        cycle_start_date = _add_years(birth.birth_date, cycle_start_age)
        cycle_end_date = _add_years(birth.birth_date, cycle_start_age + 10) - timedelta(days=1)
        cycles.append(
            LuckCycleEntry(
                label=f"第{i + 1}大運（目安{round(cycle_start_age)}歳〜{round(cycle_start_age + 10)}歳）",
                start_date=cycle_start_date,
                end_date=cycle_end_date,
                stem=stem,
                branch=branch,
                ten_god=compute_ten_god(day_stem, stem),
                twelve_stage=twelve_stage_for(day_stem, branch),
            )
        )

    return LuckCyclesResult(
        direction=direction,
        start_age_years=round(start_age_years, 2),
        start_date=start_date,
        major_cycles=cycles,
    )


def calculate_annual_cycles(
    four_pillars: FourPillarsResult, policy: CalculationPolicy, start_year: int, count: int = 3
) -> list[LuckCycleEntry]:
    day_stem = four_pillars.day_master_stem
    entries: list[LuckCycleEntry] = []
    for offset in range(count):
        year = start_year + offset
        dt = datetime(year, 7, 1, 12, 0, tzinfo=JST)  # 年運は年単位のため代表日時として7/1正午を使用
        year_stem, year_branch, _, _ = year_and_month_ganzhi_for(dt, policy)
        entries.append(
            LuckCycleEntry(
                label=f"{year}年",
                start_date=date(year, 1, 1),
                end_date=date(year, 12, 31),
                stem=year_stem,
                branch=year_branch,
                ten_god=compute_ten_god(day_stem, year_stem),
                twelve_stage=twelve_stage_for(day_stem, year_branch),
            )
        )
    return entries


def calculate_monthly_cycle(
    four_pillars: FourPillarsResult, policy: CalculationPolicy, target: date
) -> LuckCycleEntry:
    day_stem = four_pillars.day_master_stem
    dt = datetime(target.year, target.month, target.day, 12, 0, tzinfo=JST)
    year_stem, year_branch, month_stem, month_branch = year_and_month_ganzhi_for(dt, policy)
    return LuckCycleEntry(
        label=f"{target.year}年{target.month}月",
        stem=month_stem,
        branch=month_branch,
        ten_god=compute_ten_god(day_stem, month_stem),
        twelve_stage=twelve_stage_for(day_stem, month_branch),
    )
