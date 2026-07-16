"""命式計算エンジンの統合エントリポイント。
Claude/アプリ層はこのモジュールの関数のみを呼び出し、干支等の推測は行わない。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from app.calculation.four_pillars import calculate_four_pillars
from app.calculation.luck_cycles import calculate_annual_cycles, calculate_major_cycles, calculate_monthly_cycle
from app.calculation.policy import DEFAULT_POLICY, CalculationPolicy
from app.calculation.sanmeigaku import calculate_sanmeigaku
from app.calculation.schemas import BirthInput, CalculationMetadata, CalculationResult


def run_full_calculation(
    birth: BirthInput,
    policy: CalculationPolicy = DEFAULT_POLICY,
    annual_start_year: int | None = None,
    annual_count: int = 3,
    monthly_target: date | None = None,
) -> CalculationResult:
    """四柱推命・算命学・大運/年運/月運をすべて計算し、統合結果を返す。"""
    four_pillars, notes = calculate_four_pillars(birth, policy)
    sanmeigaku = calculate_sanmeigaku(four_pillars, policy)
    luck = calculate_major_cycles(birth, four_pillars, policy)

    if annual_start_year is not None:
        luck.annual_cycles = calculate_annual_cycles(four_pillars, policy, annual_start_year, annual_count)
    if monthly_target is not None:
        luck.monthly_cycles = [calculate_monthly_cycle(four_pillars, policy, monthly_target)]

    metadata = CalculationMetadata(
        policy_version=policy.version,
        calculated_at=datetime.now(timezone.utc),
        input_echo=birth,
        birth_time_known=not birth.birth_time_unknown and birth.birth_time is not None,
        accuracy_notes=notes,
    )

    return CalculationResult(
        shichuu_suimei=four_pillars,
        sanmeigaku=sanmeigaku,
        luck_cycles=luck,
        metadata=metadata,
    )
