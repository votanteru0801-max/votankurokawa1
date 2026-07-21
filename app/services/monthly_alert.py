"""今月の十二運から、気力が下がりやすい時期の人物を機械的に抽出するロジック。

AIは一切使わず、決定論的な命式計算エンジンの結果のみで判定する
（無料枠のトークン上限に依存しないための設計。詳細は
docs/calculation-policy.md 及び会話ログ参照）。

古典命理学の十二運（長生・沐浴・冠帯・臨官・帝旺・衰・病・死・墓・絶・胎・養）
のうち、伝統的に気力・活力が下がりやすいとされる4つの状態
（病・死・墓・絶）を対象月について計算し、該当する人物を一覧化する。

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

WEAK_TWELVE_STAGES = {"病", "死", "墓", "絶"}

_STAGE_NOTES = {
    "病": "十二運が「病」の時期です。無理をしがちな時期とされ、体調面への配慮が必要とされています。",
    "死": "十二運が「死」の時期です。気力が落ちやすく、ケアレスミスに注意が必要とされる時期です。",
    "墓": "十二運が「墓」の時期です。表面化しにくい疲れが溜まりやすいとされる時期です。",
    "絶": "十二運が「絶」の時期です。気力の波が大きくなりやすいとされる時期です。",
}

CAVEAT = (
    "これは命式上の目安であり、実際の体調・モチベーションを保証するものではありません。"
    "採用・配置・評価などの判断にこの結果だけを使わず、必ず本人の状況を確認してください。"
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
        if stage in WEAK_TWELVE_STAGES:
            alerts.append(
                {
                    "name": person.name,
                    "department": person.department,
                    "twelve_stage": stage,
                    "note": _STAGE_NOTES.get(stage, f"十二運が「{stage}」の時期です。"),
                }
            )
    return alerts
