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
from app.ai.output_schemas import (
    DetailedAnalysisResponse,
    SimpleAnalysisResponse,
    TeamRecommendationResponse,
)
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
        accuracy_line = (
            "この人物について精度上の制限事項は次の" + str(len(accuracy_notes)) + "件のみです: "
            + ("; ".join(accuracy_notes) if accuracy_notes else "なし（出生時間・性別とも登録済みのため、時柱や大運の方向も算出済みです）")
        )
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
            + f"\n\n{accuracy_line}\n"
            "重要: 上記の制限事項リストに無い内容（例:「出生時間が未登録」等）を、"
            "回答本文に書かないでください。リストに無ければ、その項目は登録済み・算出済みです。\n"
            "指定されたJSONスキーマの形式で回答してください。"
        )
        return self._generate(user_content, schema_cls)

    def _generate(self, user_content: str, schema_cls):
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

    def recommend_team(self, criteria: str, candidates: list[dict]) -> TeamRecommendationResponse:
        candidates_text = "氏名,所属,MBTI,日主,中心星\n" + "\n".join(
            f"{c['name']},{c.get('department') or '-'},{c.get('mbti') or '-'},"
            f"{c.get('day_master_element','?')}{c.get('day_master_yinyang','')},"
            f"{c.get('center_star') or '-'}"
            for c in candidates
        )
        user_content = (
            f"石橋輝一からの依頼: 次の条件に合う新プロジェクトメンバーの候補を、"
            f"以下の候補者一覧(CSV形式: 氏名,所属,MBTI,日主,中心星)の中から選んでください。\n条件: {criteria}\n\n"
            + wrap_as_data_not_instruction("候補者一覧（命式の要約データ、CSV形式）", candidates_text)
            + "\n重要: 候補者一覧に無い名前を作り出さないでください。必ず一覧の中の氏名をそのまま使ってください。\n"
            "各候補について、命式・MBTI等のどの情報から条件に合うと判断したか、reasonに具体的に書いてください。\n"
            "caveatsには「占術だけで採用・配置を決定しないこと」「本人の意向や実績も必ず確認すること」という"
            "趣旨の注意書きを必ず1件以上含めてください。\n"
            "指定されたJSONスキーマの形式で回答してください。"
        )
        return self._generate(user_content, TeamRecommendationResponse)
