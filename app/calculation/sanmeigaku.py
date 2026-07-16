"""算命学側の決定論的計算。LLMは一切使用しない。

中心星・十大主星・十二大従星・天中殺は公開されている標準的な算命学の計算方法
（通変星と同一の五行・陰陽関係ロジックに、算命学独自の星名を対応させたもの）で
算出する。守護神・位相法は流派差が大きく現時点では簡易実装であり、
confidenceフィールドで信頼度を明示する。
"""
from __future__ import annotations

from app.calculation.four_pillars import compute_ten_god, twelve_stage_for
from app.calculation.policy import CalculationPolicy, CenterStarMethod
from app.calculation.schemas import FourPillarsResult, SanmeigakuResult
from app.calculation.tables import (
    KUBOU_GROUPS,
    STEMS,
    TEN_GOD_TO_JUDAI_SEI,
    TWELVE_STAGE_TO_JYUNI_JYUSEI,
    ganzhi_index,
)


def calculate_sanmeigaku(
    four_pillars: FourPillarsResult, policy: CalculationPolicy
) -> SanmeigakuResult:
    day_stem = four_pillars.day_master_stem

    juudai: dict[str, str] = {}
    positions_stem = {
        "年干": four_pillars.year_pillar.stem,
        "月干": four_pillars.month_pillar.stem,
    }
    if four_pillars.hour_pillar:
        positions_stem["時干"] = four_pillars.hour_pillar.stem

    for label, stem in positions_stem.items():
        ten_god = compute_ten_god(day_stem, stem)
        if ten_god:
            juudai[label] = TEN_GOD_TO_JUDAI_SEI[ten_god]

    positions_branch_main_qi = {
        "年支": four_pillars.year_pillar.hidden_stems[0],
        "月支": four_pillars.month_pillar.hidden_stems[0],
        "日支": four_pillars.day_pillar.hidden_stems[0],
    }
    if four_pillars.hour_pillar:
        positions_branch_main_qi["時支"] = four_pillars.hour_pillar.hidden_stems[0]

    for label, hidden_stem in positions_branch_main_qi.items():
        ten_god = compute_ten_god(day_stem, hidden_stem)
        if ten_god:
            juudai[label] = TEN_GOD_TO_JUDAI_SEI[ten_god]

    juuni: dict[str, str] = {}
    branch_positions = {
        "年支": four_pillars.year_pillar.branch,
        "月支": four_pillars.month_pillar.branch,
        "日支": four_pillars.day_pillar.branch,
    }
    if four_pillars.hour_pillar:
        branch_positions["時支"] = four_pillars.hour_pillar.branch
    for label, branch in branch_positions.items():
        stage = twelve_stage_for(day_stem, branch)
        juuni[label] = TWELVE_STAGE_TO_JYUNI_JYUSEI[stage]

    # 天中殺: 日柱の60干支インデックスの十の位グループから求める
    day_index = ganzhi_index(four_pillars.day_pillar.stem, four_pillars.day_pillar.branch)
    group = day_index // 10
    tenchuusatsu = list(KUBOU_GROUPS[group])

    # 中心星
    center_star = None
    if policy.center_star_method == CenterStarMethod.MONTH_BRANCH_MAIN_QI:
        main_qi = four_pillars.month_pillar.hidden_stems[0]
    else:
        main_qi = four_pillars.day_pillar.hidden_stems[0]
    ten_god_for_center = compute_ten_god(day_stem, main_qi)
    if ten_god_for_center:
        center_star = TEN_GOD_TO_JUDAI_SEI[ten_god_for_center]
    else:
        # 月支蔵干が日干と同一の場合など、通変星が定義できないケースの簡易フォールバック
        center_star = "貫索星"

    # 守護神（簡易版: 五行バランスが最も弱い五行を補うと仮定。要検証）
    balance = four_pillars.five_element_balance
    weakest_element = min(balance.items(), key=lambda kv: (kv[1], kv[0]))[0]
    guardian_deity = weakest_element

    return SanmeigakuResult(
        center_star=center_star,
        center_star_confidence="provisional",
        juudai_shusei=juudai,
        juuni_daijuusei=juuni,
        tenchuusatsu=tenchuusatsu,
        guardian_deity=guardian_deity,
        guardian_deity_confidence="unverified",
        isouhou_note=(
            "位相法は簡易実装です。人体星図上の十大主星配置から詳細な位相判定を行う"
            "ロジックは未実装のため、現時点では参考情報として扱ってください。"
        ),
        isouhou_confidence="unverified",
        major_cycles=[],
    )
