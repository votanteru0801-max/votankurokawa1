"""今月が天中殺（空亡）かつ十二運が墓・死・絶と重なる人物を機械的に抽出するロジック。

AIは一切使わず、決定論的な命式計算エンジンの結果のみで判定する
（無料枠のトークン上限に依存しないための設計。詳細は
docs/calculation-policy.md 及び会話ログ参照）。

判定基準（ユーザー要望・2026-07-26で最終確定）:
1. 算命学側の天中殺（空亡。app/calculation/sanmeigaku.py の tenchuusatsu。
   日柱から決まる2つの地支で、その地支にあたる年・月は物事が空転しやすい
   とされる）にあたる月であること
2. かつ、十二運が「墓」「死」「絶」のいずれかであること（「病」は対象外）
上記の両方が重なる月だけをアラート対象とする（どちらか一方だけでは対象外）。

途中経過: 最初は十二運の病・死・墓・絶のみを基準にしていたが、その後
天中殺（空亡）月のみを基準にする案を経て、最終的に両方が重なる月のみを
対象とする現在の形に変更した。

重要: これはあくまで占術上の目安であり、実際の体調やモチベーションを
保証するものではない。採用・配置・評価などの人事上の判断にこの結果
だけを使わず、必ず本人に確認すること（要件4章の安全設計と同じ方針）。
"""
from __future__ import annotations

from datetime import date

from app.ai.tool_executor import _birth_input_from_person
from app.calculation.engine import run_full_calculation
from app.calculation.policy import DEFAULT_POLICY
from app.sheets.interface import PersonRepository

WEAK_TWELVE_STAGES = {"墓", "死", "絶"}  # 「病」は対象外

CAVEAT = (
    "これは命式上の目安であり、実際の体調・モチベーションを保証するものではありません。"
    "採用・配置・評価などの判断にこの結果だけを使わず、必ず本人の状況を確認してください。"
)

_NOTE_TEMPLATE = (
    "今月は十二運が「{stage}」かつ天中殺（空亡、地支「{branch}」）が重なる時期です。"
    "気力が落ちやすく物事も空転しやすいとされるため、無理をさせない配慮が必要とされています。"
)


def build_monthly_alerts(repo: PersonRepository, target: date | None = None) -> list[dict]:
    target = target or date.today()
    alerts: list[dict] = []
    for person in repo.list_all():
        if person.birth_date is None:
            continue
        try:
            birth = _birth_input_from_person(person)
            result = run_full_calculation(birth, DEFAULT_POLICY, monthly_target=target)
        except Exception:
            continue
        monthly = result.luck_cycles.monthly_cycles
        if not monthly:
            continue
        stage = monthly[0].twelve_stage
        branch = monthly[0].branch
        kubou_branches = set(result.sanmeigaku.tenchuusatsu)

        if stage in WEAK_TWELVE_STAGES and branch in kubou_branches:
            alerts.append(
                {
                    "name": person.name,
                    "department": person.department,
                    "twelve_stage": stage,
                    "note": _NOTE_TEMPLATE.format(stage=stage, branch=branch),
                }
            )
    return alerts
