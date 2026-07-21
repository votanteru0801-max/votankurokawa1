"""簡易/詳細分析（命式計算→AI分析→整形済みテキスト）の共通ロジック。
LINE版(app/ai/orchestrator.py)とWeb版(app/web/dashboard.py)の両方から使う。
"""
from __future__ import annotations

from datetime import date

from app.ai.client_interface import AnalysisGenerationError
from app.ai.prompt_design import DataPurpose
from app.ai.response_formatter import format_detailed_analysis, format_simple_analysis
from app.ai.tool_executor import ToolContext, ToolValidationError, execute_tool
from app.config import get_settings
from app.services import audit_service


class AnalysisError(Exception):
    """ユーザーにそのまま見せてよいエラーメッセージを保持する。"""


def run_analysis_for_person(db, repo, ai_client, actor_id: str, person, question: str, mode: str) -> str:
    """actor_id は監査ログ用の識別子（LINEのuserId、またはWeb版なら "web:xxx"）。
    エラー時は AnalysisError を送出する（メッセージはそのままユーザーに見せてよい）。
    """
    ctx = ToolContext(actor_id, db, repo)
    try:
        four_pillars = execute_tool("calculate_four_pillars", {"person_id": str(person.person_id)}, ctx)
        sanmeigaku = execute_tool("calculate_sanmeigaku", {"person_id": str(person.person_id)}, ctx)
        luck = execute_tool(
            "get_luck_cycles", {"person_id": str(person.person_id), "annual_year": date.today().year}, ctx
        )
    except ToolValidationError as e:
        raise AnalysisError(f"命式計算でエラーが発生しました: {e}") from e

    calculation_data = {"shichuu_suimei": four_pillars, "sanmeigaku": sanmeigaku, "luck_cycles": luck}
    purpose = DataPurpose.DETAILED_ANALYSIS if mode == "detailed" else DataPurpose.SIMPLE_ANALYSIS
    hr_context = execute_tool(
        "get_relevant_hr_context", {"person_id": str(person.person_id), "purpose": purpose.value}, ctx
    )

    # 出生時間・性別未登録などの精度上の注意は、決定論的な計算結果から確定させる。
    accuracy_notes: list[str] = []
    if four_pillars.get("hour_pillar_omitted_reason"):
        accuracy_notes.append(four_pillars["hour_pillar_omitted_reason"])
    if luck.get("unavailable_reason"):
        accuracy_notes.append(luck["unavailable_reason"])

    try:
        resp = ai_client.generate_analysis(
            mode, person.name, str(person.person_id), calculation_data, hr_context, question, accuracy_notes
        )
    except AnalysisGenerationError as e:
        raise AnalysisError("AI分析の生成に失敗しました。時間をおいて再度お試しください。") from e

    resp.accuracy_notes = accuracy_notes

    settings = get_settings()
    audit_service.log_ai_request(
        db, actor_id, intent=f"{mode}_analysis",
        tool_calls={"calculate_four_pillars": 1, "calculate_sanmeigaku": 1, "get_luck_cycles": 1},
        data_sent_summary={"fields": list(hr_context.keys())},
        model=settings.anthropic_model,
    )

    return format_detailed_analysis(resp) if mode == "detailed" else format_simple_analysis(resp)
