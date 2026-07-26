"""個人ごとの「今年の大運・毎月の運勢・伸びどき・支えが必要な時期」を
機械的（AIを使わず決定論的な命式計算エンジンのみ）に算出するロジック。

app/services/monthly_alert.py と同じ方針で、古典命理学の十二運
（長生・沐浴・冠帯・建禄・帝旺・衰・病・死・墓・絶・胎・養）のうち、
伝統的に勢いが強いとされる4つ（長生・冠帯・建禄・帝旺）を「伸びどき」、
気力・活力が下がりやすいとされる4つ（病・死・墓・絶）を「支えが必要な
時期」として分類する。残り4つ（沐浴・衰・胎・養）はどちらにも分類しない
（占術上の解釈が割れやすいため、断定的な分類を避ける）。

これに加えて、算命学側の天中殺（空亡）にあたる月・年も「支えが必要な時期」
として扱う（ユーザー要望・2026-07-26）。天中殺は日柱から決まる2つの地支
（app/calculation/sanmeigaku.py の tenchuusatsu）で、その地支にあたる
年・月は物事が空転しやすい時期とされる。十二運が「伸びどき」に該当する
月であっても天中殺と重なる場合は、その旨を注記に加える（伸びどき自体の
分類は変えない）。

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
SUPPORT_STAGES = {"病", "死", "墓", "絶"}

_GROWTH_NOTES = {
    "長生": "十二運が「長生」の時期です。新しいことを始めたり、力を伸ばすのに向いているとされています。",
    "冠帯": "十二運が「冠帯」の時期です。経験が身につき、力がついてくるとされる時期です。",
    "建禄": "十二運が「建禄」の時期です。実力を発揮しやすく、活躍が期待できるとされる時期です。",
    "帝旺": "十二運が「帝旺」の時期です。最も勢いが強く、力を発揮しやすいとされる時期です。",
}
_SUPPORT_NOTES = {
    "病": "十二運が「病」の時期です。無理をしがちな時期とされ、体調面への配慮が必要とされています。",
    "死": "十二運が「死」の時期です。気力が落ちやすく、ケアレスミスに注意が必要とされる時期です。",
    "墓": "十二運が「墓」の時期です。表面化しにくい疲れが溜まりやすいとされる時期です。",
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
    """指定人物の今年・毎月の運勢一覧と伸びどき/支えが必要な時期をまとめて返す。

    生年月日が未登録の場合や性別未登録で大運の順逆が判定できない場合は、
    該当項目を None のまま返す（呼び出し側でその旨を表示する）。
    """
    target = target or date.today()
    birth = _birth_input_from_person(person)  # 生年月日未登録なら ToolValidationError を送出

    result = run_full_calculation(
        birth,
        DEFAULT_POLICY,
        annual_start_year=target.year,
        annual_count=1,
        monthly_target=date(target.year, target.month, 1),
    )

    kubou_branches = set(result.sanmeigaku.tenchuusatsu)

    current_major = None
    for cyc in result.luck_cycles.major_cycles:
        if cyc.start_date and cyc.end_date and cyc.start_date <= target <= cyc.end_date:
            current_major = cyc
            break

    annual = result.luck_cycles.annual_cycles[0] if result.luck_cycles.annual_cycles else None

    months: list[LuckCycleEntry] = []
    for m in range(1, 13):
        try:
            months.append(calculate_monthly_cycle(result.shichuu_suimei, DEFAULT_POLICY, date(target.year, m, 1)))
        except Exception:
            continue

    growth_periods: list[dict] = []
    support_periods: list[dict] = []

    if annual is not None:
        kind, notes = _classify(annual, kubou_branches)
        entry = _entry_dict(annual, "\n".join(notes) if notes else None)
        if kind == "growth":
            growth_periods.append(entry)
        elif kind == "support":
            support_periods.append(entry)

    for m in months:
        kind, notes = _classify(m, kubou_branches)
        if kind is None:
            continue
        entry = _entry_dict(m, "\n".join(notes))
        if kind == "growth":
            growth_periods.append(entry)
        else:
            support_periods.append(entry)

    return {
        "year": target.year,
        "direction": result.luck_cycles.direction,
        "unavailable_reason": result.luck_cycles.unavailable_reason,
        "current_major_cycle": _entry_dict(current_major),
        "annual": _entry_dict(annual),
        "monthly": [_entry_dict(m) for m in months],
        "kubou_branches": sorted(kubou_branches),
        "growth_periods": growth_periods,
        "support_periods": support_periods,
        "caveat": CAVEAT,
    }
