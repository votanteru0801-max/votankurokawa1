"""二者間の「相性チェック」（命式全体+算命学に基づく決定論的計算→AI解釈）。

以前は十干（日主）だけを見た簡易的な相性判定だったが、要望（2026-07-30）により
四柱推命の命式全体（年柱・月柱・日柱・時柱）と算命学（十二運・通変星・天中殺/空亡）
まで含めて分析するように作り直した。

決定論的な計算（四柱・十二運・通変星・空亡）はこれまでの分析機能と同じく
app/ai/tool_executor.py 経由で行い、AIは「命式データの解釈」のみを担当する
（本アプリ共通の安全設計方針）。
"""
from __future__ import annotations

from datetime import date

from app.ai.client_interface import AnalysisGenerationError
from app.ai.prompt_design import DataPurpose, minimize_person_context
from app.ai.response_formatter import format_compatibility_analysis
from app.ai.tool_executor import ToolContext, ToolValidationError, execute_tool
from app.config import get_settings
from app.services import audit_service


class CompatibilityError(Exception):
    """ユーザーにそのまま見せてよいエラーメッセージを保持する。"""


def _person_calc_data(person, ctx: ToolContext) -> dict:
    four_pillars = execute_tool("calculate_four_pillars", {"person_id": str(person.person_id)}, ctx)
    sanmeigaku = execute_tool("calculate_sanmeigaku", {"person_id": str(person.person_id)}, ctx)
    luck = execute_tool(
        "get_luck_cycles", {"person_id": str(person.person_id), "annual_year": date.today().year}, ctx
    )
    return {"shichuu_suimei": four_pillars, "sanmeigaku": sanmeigaku, "luck_cycles": luck}


def run_compatibility_analysis(db, repo, ai_client, actor_id: str, person_a, person_b) -> str:
    """actor_id は監査ログ用の識別子（LINEのuserId、またはWeb版なら "web:xxx"）。
    エラー時は CompatibilityError を送出する（メッセージはそのままユーザーに見せてよい）。
    """
    if str(person_a.person_id) == str(person_b.person_id):
        raise CompatibilityError("同じ人物同士は相性チェックできません。別の氏名を指定してください。")

    ctx = ToolContext(actor_id, db, repo)
    try:
        data_a = _person_calc_data(person_a, ctx)
        data_b = _person_calc_data(person_b, ctx)
    except ToolValidationError as e:
        raise CompatibilityError(f"命式計算でエラーが発生しました: {e}") from e

    # 参考情報として、氏名・所属・役職・MBTIなど最小限の人事情報も文脈として渡す
    # （health_info・family_info等の機微情報は含めない。DataPurpose.COMPATIBILITY参照）。
    hr_a = minimize_person_context(person_a, DataPurpose.COMPATIBILITY)
    hr_b = minimize_person_context(person_b, DataPurpose.COMPATIBILITY)
    data_a["hr_context"] = hr_a
    data_b["hr_context"] = hr_b

    accuracy_notes: list[str] = []
    for label, person, data in (("Aさん", person_a, data_a), ("Bさん", person_b, data_b)):
        reason = data["shichuu_suimei"].get("hour_pillar_omitted_reason")
        if reason:
            accuracy_notes.append(f"{label}（{person.name}）: {reason}")
        unavail = data["luck_cycles"].get("unavailable_reason")
        if unavail:
            accuracy_notes.append(f"{label}（{person.name}）: {unavail}")

    try:
        resp = ai_client.generate_compatibility(
            person_a.name, str(person_a.person_id), data_a,
            person_b.name, str(person_b.person_id), data_b,
            accuracy_notes,
        )
    except AnalysisGenerationError as e:
        raise CompatibilityError("AI分析の生成に失敗しました。時間をおいて再度お試しください。") from e

    resp.accuracy_notes = accuracy_notes

    settings = get_settings()
    audit_service.log_ai_request(
        db, actor_id, intent="compatibility_analysis",
        tool_calls={"calculate_four_pillars": 2, "calculate_sanmeigaku": 2, "get_luck_cycles": 2},
        data_sent_summary={"person_a": person_a.name, "person_b": person_b.name},
        model=settings.anthropic_model,
    )

    return format_compatibility_analysis(resp)
