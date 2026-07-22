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
from app.ai.output_schemas import (
    DetailedAnalysisResponse,
    SimpleAnalysisResponse,
    TeamRecommendationResponse,
)
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

    def _call_tool(self, tool_name: str, tool_schema: dict, user_content: str, schema_cls):
        tool = {
            "name": tool_name,
            "description": "結果を指定スキーマで構造化して提出する。",
            "input_schema": tool_schema,
        }
        client = self._get_client()
        last_error: Exception | None = None
        for _ in range(self._max_retries + 1):
            response = client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool_name},
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
            "submit_analysisツールを使って回答を構造化して提出してください。"
        )
        return self._call_tool("submit_analysis", schema_cls.model_json_schema(), user_content, schema_cls)

    def recommend_team(self, criteria: str, candidates: list[dict]) -> TeamRecommendationResponse:
        from app.services.team_recommendation import candidates_to_csv

        candidates_text = candidates_to_csv(candidates)
        user_content = (
            f"石橋輝一からの依頼: 次の条件に合う新プロジェクトメンバーの候補を、"
            f"以下の候補者一覧(CSV形式、1行目が項目名)の中から選んでください。\n条件: {criteria}\n\n"
            + wrap_as_data_not_instruction("候補者一覧（命式の要約データ、CSV形式）", candidates_text)
            + "\n重要: 候補者一覧に無い名前を作り出さないでください。必ず一覧の中の氏名をそのまま使ってください。\n"
            "各候補のreasonには、候補者一覧に実際に含まれる具体的な項目（例: 年齢・年柱・月柱・日柱・時柱・"
            "日主・通変星・中心星・MBTIなど、一覧に含まれているものだけ）を引用しながら、"
            "なぜ条件に合うと判断したかを具体的に書いてください。一覧に無い情報は使わないでください。\n"
            "caveatsには「占術だけで採用・配置を決定しないこと」「本人の意向や実績も必ず確認すること」という"
            "趣旨の注意書きを必ず1件以上含めてください。\n"
            "recommend_teamツールを使って回答を構造化して提出してください。"
        )
        return self._call_tool(
            "recommend_team", TeamRecommendationResponse.model_json_schema(), user_content, TeamRecommendationResponse
        )
