"""Google Gemini APIを用いた本番AI分析クライアント（無料枠向け代替実装）。

Anthropic APIは有料（従量課金）のため、無料で使い続けられる選択肢として
Gemini API（Googleアカウントのみで利用可、クレジットカード登録不要の無料枠あり。
2026年7月時点でFlash/Flash-Liteモデルが無料枠対象）を使えるようにする。
インターフェース（generate_analysisの入出力）は app/ai/real_client.py の
AnthropicAIClient と完全互換にしてあり、app/ai/factory.py で差し替えるだけで
動作するようにしている。

構造化出力はGemini SDKの response_schema 機能（Pydanticモデルを直接渡せる）で
取得し、念のためこちらでも model_validate_json による検証を行う。検証に失敗した
場合は ANTHROPIC_MAX_TOOL_RETRIES 回まで再試行する。
"""
from __future__ import annotations

import json

from app.ai.client_interface import AnalysisGenerationError, AnalysisMode
from app.ai.output_schemas import DetailedAnalysisResponse, SimpleAnalysisResponse
from app.ai.prompt_design import SYSTEM_PROMPT, wrap_as_data_not_instruction
from app.config import get_settings


class GeminiAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.gemini_model
        self._api_key = settings.gemini_api_key
        self._max_retries = settings.anthropic_max_tool_retries
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
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
            "指定されたJSONスキーマの形式で回答してください。"
        )
        client = self._get_client()
        last_error: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=self._model,
                    contents=user_content,
                    config={
                        "system_instruction": SYSTEM_PROMPT,
                        "response_mime_type": "application/json",
                        "response_schema": schema_cls,
                    },
                )
                return schema_cls.model_validate_json(response.text)
            except Exception as e:  # Gemini側のエラー・Pydantic検証エラーの両方を捕捉
                last_error = e
                continue
        raise AnalysisGenerationError(f"構造化出力の検証に失敗しました: {last_error}")
