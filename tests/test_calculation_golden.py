"""命式計算: ゴールデンデータとの一致・出生時間有無・節入り/日付変更付近・
大運の順行逆行・年運/月運・計算ポリシー変更。
DB不要。real pydantic があれば `pytest tests/test_calculation_golden.py` 単体でも実行可能。
"""
from __future__ import annotations

from datetime import date, time

import pytest

from app.calculation.engine import run_full_calculation
from app.calculation.policy import CalculationPolicy, DEFAULT_POLICY, YearPillarBoundary
from app.calculation.schemas import BirthInput, Gender


GOLDEN_CASES = [
    # (name, birth_date, birth_time, gender, expected_day_master, expected_center_star)
    ("石橋輝一", date(1991, 8, 1), time(11, 52), Gender.MALE, None, "車騎星"),
    ("濱澤ひかり", date(1996, 12, 24), time(5, 46), Gender.FEMALE, "乙", "龍高星"),
    ("下小薗優菜", date(2002, 3, 14), time(17, 30), Gender.FEMALE, "辛", "禄存星"),
]


@pytest.mark.parametrize("name,bd,bt,gender,expected_day_master,expected_center_star", GOLDEN_CASES)
def test_golden_candidate_values(name, bd, bt, gender, expected_day_master, expected_center_star):
    """注意: ここでの期待値はユーザーの記憶による『候補値』であり、
    元サイトのスクリーンショット等による正式なゴールデンテストではない
    （golden_tests/data/*.yaml は status: unverified）。
    このテストは実装の回帰検知を目的とした参考テストである。
    """
    birth = BirthInput(birth_date=bd, birth_time=bt, birth_time_unknown=False, gender=gender)
    result = run_full_calculation(birth, DEFAULT_POLICY)
    if expected_day_master:
        assert result.shichuu_suimei.day_master_stem == expected_day_master
    assert result.sanmeigaku.center_star == expected_center_star


def test_known_year_pillars_match_common_knowledge():
    # 1984=甲子年を起点とする60干支サイクルの検算（広く知られる干支年との一致確認）
    cases = [
        (date(1991, 8, 1), "辛未"),  # 1991年は辛未年（羊年）
        (date(1996, 12, 24), "丙子"),  # 1996年は丙子年（子年）
        (date(2002, 3, 14), "壬午"),  # 2002年は壬午年（午年）
        (date(2024, 6, 1), "甲辰"),  # 2024年は甲辰年（辰年）として広く知られる
    ]
    for bd, expected in cases:
        birth = BirthInput(birth_date=bd, birth_time=time(12, 0), birth_time_unknown=False, gender=Gender.MALE)
        result = run_full_calculation(birth, DEFAULT_POLICY)
        actual = result.shichuu_suimei.year_pillar.stem + result.shichuu_suimei.year_pillar.branch
        assert actual == expected, f"{bd}: expected {expected}, got {actual}"


def test_hour_pillar_present_when_birth_time_known():
    birth = BirthInput(birth_date=date(1990, 1, 1), birth_time=time(10, 0), birth_time_unknown=False, gender=Gender.MALE)
    result = run_full_calculation(birth, DEFAULT_POLICY)
    assert result.shichuu_suimei.hour_pillar is not None
    assert result.shichuu_suimei.hour_pillar_omitted_reason is None


def test_hour_pillar_absent_when_birth_time_unknown():
    birth = BirthInput(birth_date=date(1990, 1, 1), birth_time_unknown=True, gender=Gender.MALE)
    result = run_full_calculation(birth, DEFAULT_POLICY)
    assert result.shichuu_suimei.hour_pillar is None
    assert result.shichuu_suimei.hour_pillar_omitted_reason is not None
    assert "時柱" in result.shichuu_suimei.hour_pillar_omitted_reason


def test_month_boundary_near_setsuiri_does_not_crash():
    # 立春(2月4日頃)前後で年柱・月柱が正しく計算できること（クラッシュしないこと）を確認
    for bd in [date(1991, 2, 3), date(1991, 2, 4), date(1991, 2, 5)]:
        birth = BirthInput(birth_date=bd, birth_time=time(12, 0), birth_time_unknown=False, gender=Gender.MALE)
        result = run_full_calculation(birth, DEFAULT_POLICY)
        assert result.shichuu_suimei.year_pillar is not None
        assert result.shichuu_suimei.month_pillar is not None


def test_day_boundary_near_midnight_with_23h_policy():
    policy_0h = DEFAULT_POLICY
    policy_23h = CalculationPolicy(day_boundary_hour=23)

    birth_2300 = BirthInput(birth_date=date(2020, 1, 1), birth_time=time(23, 30), birth_time_unknown=False, gender=Gender.MALE)
    r0 = run_full_calculation(birth_2300, policy_0h)
    r23 = run_full_calculation(birth_2300, policy_23h)
    # 23時基準では日付が繰り上がるため、日柱が0時基準と異なりうる
    assert r0.shichuu_suimei.day_pillar is not None
    assert r23.shichuu_suimei.day_pillar is not None


def test_luck_cycle_direction_forward_and_backward():
    # 陽男（年干が陽）は順行、陰男は逆行になることを確認する
    birth_male = BirthInput(birth_date=date(1991, 8, 1), birth_time=time(11, 52), birth_time_unknown=False, gender=Gender.MALE)
    result_male = run_full_calculation(birth_male, DEFAULT_POLICY)
    assert result_male.luck_cycles.direction in ("順行", "逆行")

    birth_female = BirthInput(birth_date=date(1991, 8, 1), birth_time=time(11, 52), birth_time_unknown=False, gender=Gender.FEMALE)
    result_female = run_full_calculation(birth_female, DEFAULT_POLICY)
    # 同じ生年月日でも性別が異なれば大運の方向が逆になる
    assert result_male.luck_cycles.direction != result_female.luck_cycles.direction


def test_luck_cycle_unavailable_without_gender():
    birth = BirthInput(birth_date=date(1990, 1, 1), birth_time_unknown=True, gender=Gender.UNKNOWN)
    result = run_full_calculation(birth, DEFAULT_POLICY)
    assert result.luck_cycles.unavailable_reason is not None
    assert result.luck_cycles.major_cycles == []


def test_annual_and_monthly_cycles():
    birth = BirthInput(birth_date=date(1991, 8, 1), birth_time=time(11, 52), birth_time_unknown=False, gender=Gender.MALE)
    result = run_full_calculation(birth, DEFAULT_POLICY, annual_start_year=2026, annual_count=2, monthly_target=date(2026, 7, 16))
    assert len(result.luck_cycles.annual_cycles) == 2
    assert result.luck_cycles.annual_cycles[0].label == "2026年"
    assert len(result.luck_cycles.monthly_cycles) == 1


def test_calculation_policy_year_boundary_variant():
    birth = BirthInput(birth_date=date(1991, 1, 15), birth_time=time(12, 0), birth_time_unknown=False, gender=Gender.MALE)
    result_risshun = run_full_calculation(birth, DEFAULT_POLICY)
    result_jan1 = run_full_calculation(birth, CalculationPolicy(year_pillar_boundary=YearPillarBoundary.JAN1))
    # 立春前の1月なので、立春基準では前年扱い、1月1日基準では当年扱いとなり年柱が異なりうる
    year_risshun = result_risshun.shichuu_suimei.year_pillar.stem + result_risshun.shichuu_suimei.year_pillar.branch
    year_jan1 = result_jan1.shichuu_suimei.year_pillar.stem + result_jan1.shichuu_suimei.year_pillar.branch
    assert year_risshun != year_jan1


def test_metadata_includes_accuracy_notes_for_unverified_day_pillar_anchor():
    birth = BirthInput(birth_date=date(2000, 1, 1), birth_time_unknown=True, gender=Gender.MALE)
    result = run_full_calculation(birth, DEFAULT_POLICY)
    assert any("日柱" in n for n in result.metadata.accuracy_notes)
