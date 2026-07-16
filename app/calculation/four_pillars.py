"""四柱推命・陰陽五行の決定論的計算。LLMは一切使用しない。"""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.calculation import solar_terms
from app.calculation.policy import CalculationPolicy, YearPillarBoundary
from app.calculation.schemas import BirthInput, FourPillarsResult, PillarResult
from app.calculation.tables import (
    BRANCH_ELEMENT,
    BRANCH_YINYANG,
    BRANCHES,
    CONTROLS,
    GENERATES,
    HIDDEN_STEMS,
    HOUR_BRANCH_BOUNDARIES,
    HOUR_STEM_BASE_BY_DAY_STEM,
    MONTH_BRANCH_SEQUENCE,
    MONTH_STEM_BASE_BY_YEAR_STEM,
    MONTH_TERM_LONGITUDES,
    STEM_ELEMENT,
    STEM_YINYANG,
    STEMS,
    TWELVE_STAGE_NAMES,
    TWELVE_STAGE_START,
)

JST = ZoneInfo("Asia/Tokyo")

# 日柱起点（要検証プレースホルダー）。
# 1900-01-01 を60干支サイクルのインデックス10（乙丑）と仮定している。
# この値は公開情報のみでは確証が取れなかったため、ゴールデンテストデータが
# 揃い次第 `golden_tests/cli.py calibrate` で校正すること。
DAY_PILLAR_ANCHOR_DATE = date(1900, 1, 1)
DAY_PILLAR_ANCHOR_INDEX = 10  # 未検証


def compute_ten_god(day_stem: str, target_stem: str) -> str | None:
    if day_stem == target_stem:
        return None  # 日柱自身は通変星を表示しない
    de, dy = STEM_ELEMENT[day_stem], STEM_YINYANG[day_stem]
    te, ty = STEM_ELEMENT[target_stem], STEM_YINYANG[target_stem]
    same_yy = dy == ty
    if te == de:
        return "比肩" if same_yy else "劫財"
    if GENERATES[de] == te:
        return "食神" if same_yy else "傷官"
    if GENERATES[te] == de:
        return "偏印" if same_yy else "正印"
    if CONTROLS[de] == te:
        return "偏財" if same_yy else "正財"
    if CONTROLS[te] == de:
        return "偏官" if same_yy else "正官"
    raise AssertionError("unreachable: 五行関係の網羅漏れ")


def twelve_stage_for(day_stem: str, branch: str) -> str:
    start_branch, forward = TWELVE_STAGE_START[day_stem]
    start_idx = BRANCHES.index(start_branch)
    branch_idx = BRANCHES.index(branch)
    offset = (branch_idx - start_idx) % 12 if forward else (start_idx - branch_idx) % 12
    return TWELVE_STAGE_NAMES[offset]


def _build_pillar(stem: str, branch: str, day_stem: str | None) -> PillarResult:
    return PillarResult(
        stem=stem,
        branch=branch,
        stem_element=STEM_ELEMENT[stem],
        branch_element=BRANCH_ELEMENT[branch],
        stem_yinyang=STEM_YINYANG[stem],
        branch_yinyang=BRANCH_YINYANG[branch],
        hidden_stems=HIDDEN_STEMS[branch],
        ten_god=compute_ten_god(day_stem, stem) if day_stem else None,
        twelve_stage=twelve_stage_for(day_stem, branch) if day_stem else None,
    )


def _astrological_year(birth_dt: datetime, policy: CalculationPolicy) -> int:
    if policy.year_pillar_boundary == YearPillarBoundary.JAN1:
        return birth_dt.year
    boundary = solar_terms.risshun_jst(birth_dt.year)
    return birth_dt.year if birth_dt >= boundary else birth_dt.year - 1


def _effective_day_date(birth: BirthInput, policy: CalculationPolicy) -> date:
    if policy.day_boundary_hour == 23 and birth.birth_time is not None and birth.birth_time.hour == 23:
        from datetime import timedelta

        return birth.birth_date + timedelta(days=1)
    return birth.birth_date


def _hour_branch_index(t: time) -> int:
    h = t.hour
    for start_hour, idx in HOUR_BRANCH_BOUNDARIES:
        end_hour = (start_hour + 2) % 24
        if start_hour == 23:
            if h == 23 or h < 1:
                return idx
        elif start_hour < end_hour:
            if start_hour <= h < end_hour:
                return idx
    raise AssertionError("時刻から時柱を特定できません")


def calculate_four_pillars(
    birth: BirthInput, policy: CalculationPolicy
) -> tuple[FourPillarsResult, list[str]]:
    notes: list[str] = []
    representative_time = birth.birth_time or time(12, 0)
    birth_dt = datetime.combine(birth.birth_date, representative_time, tzinfo=JST)
    if birth.birth_time_unknown or birth.birth_time is None:
        notes.append(
            "出生時間が未登録のため、年柱・月柱境界の判定は正午を仮の代表時刻として使用しています"
            "（節入り当日の場合のみ影響する可能性があります）。時柱は算出していません。"
        )

    astro_year = _astrological_year(birth_dt, policy)
    year_index = (astro_year - 1984) % 60  # 1984年 = 甲子年（広く知られた事実）を起点とする
    year_stem, year_branch = STEMS[year_index % 10], BRANCHES[year_index % 12]

    boundaries = solar_terms.month_term_boundaries_around(birth_dt)
    prior = [e for e in boundaries if e[1] <= birth_dt]
    if not prior:
        raise ValueError("節入り境界の計算に失敗しました（対応年代を確認してください）")
    longitude, _term_dt = prior[-1]
    month_index = MONTH_TERM_LONGITUDES.index(longitude)
    month_branch = MONTH_BRANCH_SEQUENCE[month_index]
    month_stem_base = MONTH_STEM_BASE_BY_YEAR_STEM[STEMS.index(year_stem)]
    month_stem = STEMS[(month_stem_base + month_index) % 10]

    effective_date = _effective_day_date(birth, policy)
    ordinal_diff = effective_date.toordinal() - DAY_PILLAR_ANCHOR_DATE.toordinal()
    day_index = (ordinal_diff + DAY_PILLAR_ANCHOR_INDEX) % 60
    day_stem, day_branch = STEMS[day_index % 10], BRANCHES[day_index % 12]
    notes.append(
        "日柱の起点定数は未検証のプレースホルダーです。golden_tests/cli.py calibrate で"
        "確定データを用いた校正が必要です（詳細は docs/calculation-policy.md）。"
    )

    year_pillar = _build_pillar(year_stem, year_branch, day_stem)
    month_pillar = _build_pillar(month_stem, month_branch, day_stem)
    day_pillar = _build_pillar(day_stem, day_branch, day_stem)

    hour_pillar = None
    hour_omitted_reason = None
    if birth.birth_time_unknown or birth.birth_time is None:
        hour_omitted_reason = "出生時間が未登録のため時柱は算出していません。"
    else:
        branch_idx = _hour_branch_index(birth.birth_time)
        hour_branch = BRANCHES[branch_idx]
        hour_stem_base = HOUR_STEM_BASE_BY_DAY_STEM[STEMS.index(day_stem)]
        hour_stem = STEMS[(hour_stem_base + branch_idx) % 10]
        hour_pillar = _build_pillar(hour_stem, hour_branch, day_stem)

    balance: dict[str, int] = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for pillar in [year_pillar, month_pillar, day_pillar] + ([hour_pillar] if hour_pillar else []):
        balance[pillar.stem_element] += 1
        balance[pillar.branch_element] += 1

    result = FourPillarsResult(
        year_pillar=year_pillar,
        month_pillar=month_pillar,
        day_pillar=day_pillar,
        hour_pillar=hour_pillar,
        day_master_stem=day_stem,
        day_master_element=STEM_ELEMENT[day_stem],
        day_master_yinyang=STEM_YINYANG[day_stem],
        five_element_balance=balance,
        hour_pillar_omitted_reason=hour_omitted_reason,
    )
    return result, notes


def year_and_month_ganzhi_for(dt: datetime, policy: CalculationPolicy) -> tuple[str, str, str, str]:
    """任意の日時について年柱・月柱の干支を求める（年運・月運の計算に再利用する）。"""
    astro_year = _astrological_year(dt, policy)
    year_index = (astro_year - 1984) % 60
    year_stem, year_branch = STEMS[year_index % 10], BRANCHES[year_index % 12]

    boundaries = solar_terms.month_term_boundaries_around(dt)
    prior = [e for e in boundaries if e[1] <= dt]
    if not prior:
        raise ValueError("節入り境界の計算に失敗しました")
    longitude, _ = prior[-1]
    month_index = MONTH_TERM_LONGITUDES.index(longitude)
    month_branch = MONTH_BRANCH_SEQUENCE[month_index]
    month_stem_base = MONTH_STEM_BASE_BY_YEAR_STEM[STEMS.index(year_stem)]
    month_stem = STEMS[(month_stem_base + month_index) % 10]
    return year_stem, year_branch, month_stem, month_branch
