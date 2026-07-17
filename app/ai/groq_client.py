"""Groq APIを用いた本番AI分析クライアント（無料・学習不使用を優先する場合の選択肢）。

Groqはクレジットカード登録不要の無料枠を提供しており、利用規約上も入力・出力を
AIモデルの学習に使用しないことが明記されている（2026年7月時点）。ただし利用できる
モデルはAnthropic Claudeそのものではなく、Llama等のオープンモデルである点に注意。

インターフェース（generate_analysisの入出力）は app/ai/real_client.py の
AnthropicAIClient と互換にしてあり、app/ai/factory.py で差し替えるだけで動作する。
構造化出力はOpenAI互換のtool calling（強制tool_choice）で取得する。
"""
from __future__ import annotations

import json

from app.ai.client_interface import AnalysisGenerationError, AnalysisMode
from app.ai.output_schemas import DetailedAnalysisResponse, SimpleAnalysisResponse
from app.ai.prompt_design import SYSTEM_PROMPT, wrap_as_data_not_instruction
from app.config import get_settings


class GroqAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.groq_model
        self._api_key = settings.groq_api_key
        self._max_retries = settings.anthropic_max_tool_retries
        self._client = None

    def _get_client(self):
        if self._client is None:
            from groq import Groq

            self._client = Groq(api_key=self._api_key)
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
            "type": "function",
            "function": {
                "name": "submit_analysis",
                "description": "分析結果を指定スキーマで構造化して提出する。",
                "parameters": schema_cls.model_json_schema(),
            },
        }
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
        client = self._get_client()
        last_error: Exception | None = None
        for _ in range(self._max_retries + 1):
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                tools=[tool],
                tool_choice={"type": "function", "function": {"name": "submit_analysis"}},
                # 無料枠のTPM(1分あたりトークン数)上限が低いモデルのため、
                # 入力+出力の合計が収まるよう控えめな値にしている。
                max_tokens=3500,
            )
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            if not tool_calls:
                last_error = AnalysisGenerationError("AIがツールを呼び出しませんでした。")
                continue
            try:
                raw_args = tool_calls[0].function.arguments
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    # 一部のモデルは有効なJSONの後に余分な文字列を付け足すことがあるため、
                    # 先頭から読める分だけを取り出して救済を試みる。
                    args, _ = json.JSONDecoder().raw_decode(raw_args)
                return schema_cls(**args)
            except Exception as e:  # JSON解析エラー・pydantic ValidationError等
                last_error = e
                continue
        raise AnalysisGenerationError(f"構造化出力の検証に失敗しました: {last_error}")
