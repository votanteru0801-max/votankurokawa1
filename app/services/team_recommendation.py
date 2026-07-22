"""新プロジェクトメンバー推薦機能で使う、命式要約付き候補者一覧の構築ロジック。

LINE版(app/ai/orchestrator.py)とWeb版(app/web/dashboard.py)の両方から
同じロジックを使うため、ここに共通化している。

データ最小化: 氏名・所属・MBTI・命式の要約（五行・中心星等）のみを扱い、
健康情報・家族情報・面談記録・退職相談記録などの機微情報は一切含めない。

無料AI(Groq)のトークン上限(TPM)対策として、2段階で判定する。
1. 全社員分を「簡易データ」で広く絞り込む（軽量・低トークン）。
2. 絞り込んだ少人数だけ「詳細データ」（年齢・四柱・通変星等）で
   最終判定させ、具体的な根拠を書かせる（絞り込み後なので高トークンでも安全）。
"""
from __future__ import annotations

from datetime import date

from app.ai.output_schemas import TeamRecommendationResponse
from app.ai.tool_executor import _birth_input_from_person
from app.calculation.engine import run_full_calculation
from app.calculation.policy import DEFAULT_POLICY
from app.sheets.interface import PersonRepository


def _age_from_birth_date(birth_date: date) -> int:
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def candidates_to_csv(candidates: list[dict]) -> str:
    """候補者辞書のリストをCSV形式のテキストに変換する（1行目が項目名）。
    フィールド構成は呼び出し元（簡易版/詳細版）によって異なってよい。"""
    if not candidates:
        return ""
    headers = list(candidates[0].keys())
    lines = [",".join(headers)]
    for c in candidates:
        lines.append(",".join(str(c.get(h, "-")) for h in headers))
    return "\n".join(lines)


def build_lightweight_candidates(repo: PersonRepository) -> list[dict]:
    """全社員分を一度に扱うための、最小限のフィールドのみの候補者一覧（絞り込み用）。"""
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
                "氏名": person.name,
                "所属": person.department or "-",
                "MBTI": person.mbti or "-",
                "日主": f"{result.shichuu_suimei.day_master_element}{result.shichuu_suimei.day_master_yinyang}",
                "中心星": result.sanmeigaku.center_star or "-",
            }
        )
    return candidates


def build_detailed_candidate(person) -> dict | None:
    """1名分の詳細な命式データ（年齢・四柱・通変星等）。
    絞り込み後の少人数にのみ使う、具体的な根拠を示すための詳細版。"""
    if person.birth_date is None:
        return None
    try:
        birth = _birth_input_from_person(person)
        result = run_full_calculation(birth, DEFAULT_POLICY)
    except Exception:
        return None
    fp = result.shichuu_suimei
    hour = f"{fp.hour_pillar.stem}{fp.hour_pillar.branch}" if fp.hour_pillar else "不明(出生時間未登録)"
    return {
        "氏名": person.name,
        "年齢": _age_from_birth_date(person.birth_date),
        "所属": person.department or "-",
        "MBTI": person.mbti or "-",
        "年柱": f"{fp.year_pillar.stem}{fp.year_pillar.branch}",
        "月柱": f"{fp.month_pillar.stem}{fp.month_pillar.branch}",
        "日柱": f"{fp.day_pillar.stem}{fp.day_pillar.branch}",
        "時柱": hour,
        "日主": f"{fp.day_master_element}{fp.day_master_yinyang}",
        "月柱の通変星": fp.month_pillar.ten_god or "-",
        "中心星": result.sanmeigaku.center_star or "-",
    }


def recommend_team_two_stage(
    repo: PersonRepository, ai_client, criteria: str, screen_limit: int = 12
) -> TeamRecommendationResponse:
    """全社員分を一度に詳細データでAI判定するとトークン上限に達しやすいため、
    (1) 簡易データで広く絞り込み → (2) 絞り込んだ人だけ詳細データで
    具体的な根拠付きの最終判定、という2段階で行う。
    """
    light_candidates = build_lightweight_candidates(repo)
    if not light_candidates:
        return TeamRecommendationResponse(criteria=criteria, recommended=[], caveats=[])

    screening_criteria = (
        f"{criteria}\n"
        f"（この段階では絞り込みのみで構いません。条件に合いそうな人を最大{screen_limit}名程度、"
        "少し広めにリストアップしてください。reasonは簡潔で構いません。）"
    )
    stage1 = ai_client.recommend_team(screening_criteria, light_candidates)

    shortlisted_names = [c.name for c in stage1.recommended][:screen_limit]
    if not shortlisted_names:
        return stage1

    people_by_name = {p.name: p for p in repo.list_all()}
    detailed_candidates = []
    for name in shortlisted_names:
        person = people_by_name.get(name)
        if person is None:
            continue
        d = build_detailed_candidate(person)
        if d:
            detailed_candidates.append(d)

    if not detailed_candidates:
        return stage1

    final_criteria = (
        f"{criteria}\n"
        "（ここでは絞り込み済みの候補者について、年齢・四柱（年柱/月柱/日柱/時柱）・日主・"
        "通変星・中心星など、実際に一覧に含まれる具体的なデータを引用しながら、"
        "最終的に条件に合う人数分だけ選び、根拠を具体的に書いてください。）"
    )
    return ai_client.recommend_team(final_criteria, detailed_candidates)
