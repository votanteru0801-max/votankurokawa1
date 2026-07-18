"""新プロジェクトメンバー推薦機能で使う、命式要約付き候補者一覧の構築ロジック。

LINE版(app/ai/orchestrator.py)とWeb版(app/web/dashboard.py)の両方から
同じロジックを使うため、ここに共通化している。

データ最小化: 氏名・所属・MBTI・命式の要約（五行・中心星）のみを扱い、
健康情報・家族情報・面談記録・退職相談記録などの機微情報は一切含めない。
"""
from __future__ import annotations

from app.ai.tool_executor import _birth_input_from_person
from app.calculation.engine import run_full_calculation
from app.calculation.policy import DEFAULT_POLICY
from app.sheets.interface import PersonRepository


def build_lightweight_candidates(repo: PersonRepository) -> list[dict]:
    candidates: list[dict] = []
    for person in repo.list_all():
        if person.birth_date is None:
            continue
        try:
            birth = _birth_input_from_person(person)
            result = run_full_calculation(birth, DEFAULT_POLICY)
        except Exception:
            continue
        candidates.append(
            {
                "name": person.name,
                "department": person.department,
                "mbti": person.mbti,
                "day_master_element": result.shichuu_suimei.day_master_element,
                "day_master_yinyang": result.shichuu_suimei.day_master_yinyang,
                "center_star": result.sanmeigaku.center_star,
            }
        )
    return candidates
