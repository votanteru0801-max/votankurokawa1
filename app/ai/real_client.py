"""Anthropic Claude APIを用いた本番AI分析クライアント。

モデル名はコードに固定せず環境変数 ANTHROPIC_MODEL で指定する。
構造化出力は「強制ツール呼び出し（tool_choice指定）」で取得し、Pydanticで検証する。
検証に失敗した場合は ANTHROPIC_MAX_TOOL_RETRIES 回まで再試行し、
それでも失敗したら AnalysisGenerationError を送出する（呼び出し元で安全な
エラーメッセージに変換する）。
"""
from __future__ import annotations

import json

from app.ai.client_interface import AnalysisGenerationError, AnalysisMode
from app.ai.output_schemas import DetailedAnalysisResponse, SimpleAnalysisResponse
from app.ai.prompt_design import SYSTEM_PROMPT, wrap_as_data_not_instruction
from app.config import get_settings


class AnthropicAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.anthropic_model
        self._api_key = settings.anthropic_api_key
        self._max_retries = settings.anthropic_max_tool_retries
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def generate_analysis(
        self,
        mode: AnalysisMode,
        person_name: str,
        person_id: str,
        calculation_data: dict,
        hr_context: dict,
        question: str,
        accuracy_notes: list[str],
    ):
        schema_cls = DetailedAnalysisResponse if mode == "detailed" else SimpleAnalysisResponse
        tool = {
            "name": "submit_analysis",
            "description": "分析結果を指定スキーマで構造化して提出する。",
            "input_schema": schema_cls.model_json_schema(),
        }
        user_content = (
            f"対象人物: {person_name}（person_id: {person_id}）\n"
            f"石橋輝一からの質問: {question}\n\n"
            + wrap_as_data_not_instruction(
                "命式計算結果(決定論的エンジンによる構造化データ)",
                json.dumps(calculation_data, ensure_ascii=False, default=str),
            )
            + "\n"
            + wrap_as_data_not_instruction(
                "人事情報(質問目的に応じて最小化済み)", json.dumps(hr_context, ensure_ascii=False, default=str)
            )
            + f"\n\n精度に関する注意事項: {accuracy_notes}\n"
            "submit_analysisツールを使って回答を構造化して提出してください。"
        )
        client = self._get_client()
        last_error: Exception | None = None
        for _ in range(self._max_retries + 1):
            response = client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
                tools=[tool],
                tool_choice={"type": "tool", "name": "submit_analysis"},
            )
            tool_use = next((b for b in response.content if b.type == "tool_use"), None)
            if tool_use is None:
                last_error = AnalysisGenerationError("Claudeがツールを呼び出しませんでした。")
                continue
            try:
                return schema_cls(**tool_use.input)
            except Exception as e:  # pydantic ValidationError等
                last_error = e
                continue
        raise AnalysisGenerationError(f"構造化出力の検証に失敗しました: {last_error}")
