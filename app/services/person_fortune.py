"""個人ごとの「今年・来年の大運/運勢・伸びどき・支えが必要な時期」を
機械的（AIを使わず決定論的な命式計算エンジンのみ）に算出するロジック。

対象期間は今年と来年の2年分（年運・毎月の運勢とも）。

「伸びどき」は古典命理学の十二運（長生・沐浴・冠帯・建禄・帝旺・衰・病・
死・墓・絶・胎・養）のうち、伝統的に勢いが強いとされる4つ
（長生・冠帯・建禄・帝旺）に該当する年・月とする。

「支えが必要な時期」は、ユーザー要望（2026-07-26）によりシンプルな2条件に
絞っている。
1. 十二運が「絶」にあたる年・月（気力の波が大きくなりやすいとされる）
2. 算命学側の天中殺（空亡）にあたる年・月（app/calculation/sanmeigaku.py の
   tenchuusatsu。日柱から決まる2つの地支で、物事が空転しやすいとされる時期）
（病・死・墓は対象外。以前は含めていたが、通知が多すぎるとの理由で除外した）

重要: これはあくまで占術上の目安であり、実際の体調やパフォーマンスを
保証するものではない。人事上の判断にこの結果だけを使わないこと
（docs/requirements.md 4章の安全設計と同じ方針）。
"""
from __future__ import annotations

from datetime import date

from app.ai.tool_executor import _birth_input_from_person
from app.calculation.engine import run_full_calculation
from app.calculation.luck_cycles import calculate_monthly_cycle
from app.calculation.policy import DEFAULT_POLICY
from app.calculation.schemas import LuckCycleEntry
from app.schemas.person import Person

GROWTH_STAGES = {"長生", "冠帯", "建禄", "帝旺"}
SUPPORT_STAGES = {"絶"}  # ユーザー要望により「絶」のみ（病・死・墓は対象外）

_GROWTH_NOTES = {
    "長生": "十二運が「長生」の時期です。新しいことを始めたり、力を伸ばすのに向いているとされています。",
    "冠帯": "十二運が「冠帯」の時期です。経験が身につき、力がついてくるとされる時期です。",
    "建禄": "十二運が「建禄」の時期です。実力を発揮しやすく、活躍が期待できるとされる時期です。",
    "帝旺": "十二運が「帝旺」の時期です。最も勢いが強く、力を発揮しやすいとされる時期です。",
}
_SUPPORT_NOTES = {
    "絶": "十二運が「絶」の時期です。気力の波が大きくなりやすいとされる時期です。",
}
_KUBOU_NOTE_TEMPLATE = (
    "地支が「{branch}」で、天中殺（空亡）にあたる時期です。"
    "物事が空転しやすく、無理な決断は避けた方がよいとされています。"
)

CAVEAT = (
    "これは命式上の目安であり、実際の体調・モチベーション・成果を保証するものではありません。"
    "採用・配置・評価などの判断にこの結果だけを使わず、必ず本人の状況を確認してください。"
)

YEARS_AHEAD = 2  # 今年・来年の2年分


def _classify(entry: LuckCycleEntry, kubou_branches: set[str]) -> tuple[str | None, list[str]]:
    """(growth/support/None, 注記のリスト) を返す。"""
    notes: list[str] = []
    kind: str | None = None
    if entry.twelve_stage in GROWTH_STAGES:
        kind = "growth"
        notes.append(_GROWTH_NOTES[entry.twelve_stage])
    elif entry.twelve_stage in SUPPORT_STAGES:
        kind = "support"
        notes.append(_SUPPORT_NOTES[entry.twelve_stage])

    if entry.branch in kubou_branches:
        notes.append(_KUBOU_NOTE_TEMPLATE.format(branch=entry.branch))
        if kind is None:
            kind = "support"

    return kind, notes


def _entry_dict(e: LuckCycleEntry | None, note: str | None = None) -> dict | None:
    if e is None:
        return None
    return {
        "label": e.label,
        "stem": e.stem,
        "branch": e.branch,
        "ten_god": e.ten_god,
        "twelve_stage": e.twelve_stage,
        "note": note,
    }


def build_person_fortune(person: Person, target: date | None = None) -> dict:
    """指定人物の今年・来年の運勢一覧と伸びどき/支えが必要な時期をまとめて返す。

    生年月日が未登録の場合や性別未登録で大運の順逆が判定できない場合は、
    該当項目を None のまま返す（呼び出し側でその旨を表示する）。
    """
    target = target or date.today()
    birth = _birth_input_from_person(person)  # 生年月日未登録なら ToolValidationError を送出

    result = run_full_calculation(
        birth,
        DEFAULT_POLICY,
        annual_start_year=target.year,
        annual_count=YEARS_AHEAD,
        monthly_target=date(target.year, target.month, 1),
    )

    kubou_branches = set(result.sanmeigaku.tenchuusatsu)

    current_major = None
    for cyc in result.luck_cycles.major_cycles:
        if cyc.start_date and cyc.end_date and cyc.start_date <= target <= cyc.end_date:
            current_major = cyc
            break

    annual_list: list[LuckCycleEntry] = list(result.luck_cycles.annual_cycles)

    months: list[LuckCycleEntry] = []
    for year in range(target.year, target.year + YEARS_AHEAD):
        for m in range(1, 13):
            try:
                months.append(calculate_monthly_cycle(result.shichuu_suimei, DEFAULT_POLICY, date(year, m, 1)))
            except Exception:
                continue

    growth_periods: list[dict] = []
    support_periods: list[dict] = []

    for a in annual_list:
        kind, notes = _classify(a, kubou_branches)
        if kind is None:
            continue
        entry = _entry_dict(a, "\n".join(notes))
        (growth_periods if kind == "growth" else support_periods).append(entry)

    for m in months:
        kind, notes = _classify(m, kubou_branches)
        if kind is None:
            continue
        entry = _entry_dict(m, "\n".join(notes))
        (growth_periods if kind == "growth" else support_periods).append(entry)

    return {
        "year": target.year,
        "years_covered": [target.year + i for i in range(YEARS_AHEAD)],
        "direction": result.luck_cycles.direction,
        "unavailable_reason": result.luck_cycles.unavailable_reason,
        "current_major_cycle": _entry_dict(current_major),
        "annual": [_entry_dict(a) for a in annual_list],
        "monthly": [_entry_dict(m) for m in months],
        "kubou_branches": sorted(kubou_branches),
        "growth_periods": growth_periods,
        "support_periods": support_periods,
        "caveat": CAVEAT,
    }
