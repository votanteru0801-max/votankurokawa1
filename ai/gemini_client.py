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
    CompatibilityAnalysisResponse,
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
        detail_instruction = ""
        if mode == "detailed":
            detail_instruction = (
                "重要（詳細分析の粒度）: strengths/weaknesses/growth_guidance/risk_notes/suitable_roles/"
                "approach_and_communication/hr_proposals等の各項目は、命式のどの要素（十干・十二支・"
                "十二運・通変星・大運や年運など）が根拠かを具体的に示しながら、1項目につき2〜4文程度で"
                "掘り下げて記述してください。表面的な一般論ではなく、この人物固有の命式データに"
                "基づいた記述にしてください。\n"
            )
        kubou_months = calculation_data.get("kubou_months") or []
        kubou_instruction = ""
        if kubou_months:
            kubou_instruction = (
                "重要（空亡の書き方）: 天中殺（空亡）について言及する際は、地支名だけで説明せず、"
                "渡されたkubou_months（" + "、".join(kubou_months) + "）の中から該当する具体的な年月を"
                "使って説明してください。\n"
            )
        user_content = (
            f"対象人物: {person_name}（person_id: {person_id}）\n"
            f"石橋輝一からの質問: {question}\n\n"
            + wrap_as_data_not_instruction(
                "命式計算結果(決定論的エンジンによる構造化データ、kubou_monthsは今年・来年の空亡月一覧)",
                json.dumps(calculation_data, ensure_ascii=False, default=str),
            )
            + "\n"
            + wrap_as_data_not_instruction(
                "人事情報(質問目的に応じて最小化済み)", json.dumps(hr_context, ensure_ascii=False, default=str)
            )
            + f"\n\n{accuracy_line}\n"
            "重要: 上記の制限事項リストに無い内容（例:「出生時間が未登録」等）を、"
            "回答本文に書かないでください。リストに無ければ、その項目は登録済み・算出済みです。\n"
            "重要（強み・弱みの書き方）: strengths（強み）は命式・大運等の裏付けを添えて必ず記入してください。"
            "weaknesses/cautions（弱み・注意点）は、大運・年運・十二運などに際立った弱みの兆候が"
            "明確に見当たる場合のみ記入し、そうでなければ無理に弱みを作り出さず空のままにしてください。"
            "growth_guidanceには、強みや伸びどき（十二運が長生・冠帯・建禄・帝旺にあたる時期）を踏まえた、"
            "この人物の具体的な伸ばし方・関わり方を記入してください。"
            "risk_notesには、この人物が業務上起こしやすいミス・エラーの傾向や、"
            "他のスタッフとの間で衝突・すれ違いが起きやすい傾向を、命式上の根拠とともに具体的に"
            "記入してください（根拠が乏しければ無理に作り出さず空のままでよい）。\n"
            + detail_instruction + kubou_instruction +
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
            "指定されたJSONスキーマの形式で回答してください。"
        )
        return self._generate(user_content, TeamRecommendationResponse)

    def generate_compatibility(
        self,
        person_a_name: str,
        person_a_id: str,
        data_a: dict,
        person_b_name: str,
        person_b_id: str,
        data_b: dict,
        accuracy_notes: list[str],
    ) -> CompatibilityAnalysisResponse:
        accuracy_line = (
            "精度上の制限事項は次の" + str(len(accuracy_notes)) + "件のみです: "
            + ("; ".join(accuracy_notes) if accuracy_notes else "なし（両者とも出生時間・性別が登録済みです）")
        )
        user_content = (
            f"対象人物A: {person_a_name}（person_id: {person_a_id}）\n"
            f"対象人物B: {person_b_name}（person_id: {person_b_id}）\n"
            "石橋輝一からの依頼: この二人の相性を、四柱推命・算命学の命式全体（年柱・月柱・日柱・時柱、"
            "十二運、通変星、天中殺/空亡）に基づいて分析してください。\n\n"
            + wrap_as_data_not_instruction("Aさんの命式計算結果", json.dumps(data_a, ensure_ascii=False, default=str))
            + "\n"
            + wrap_as_data_not_instruction("Bさんの命式計算結果", json.dumps(data_b, ensure_ascii=False, default=str))
            + f"\n\n{accuracy_line}\n"
            "重要（分析の観点）: 十干（日主）同士の五行の関係（比和・相生・相剋）だけでなく、"
            "年柱・月柱・日柱・時柱すべての干支の組み合わせ、十二運、通変星、天中殺（空亡）が"
            "重なっているかどうかも踏まえて、古典的な算命学・四柱推命の考え方で分析してください。"
            "十干だけを見た単純な相性判定にとどめないでください。\n"
            "重要（良い点・注意点の書き方）: good_points（相性の良い点）は命式の裏付けを添えて"
            "必ず1件以上記入してください。friction_points（注意したいすれ違いポイント）は、"
            "命式から明確な根拠が見つかる場合のみ記入し、無理に作り出さないでください。\n"
            "重要: 相性だけで人事配置・評価・採用可否を自動的に決定しないよう、"
            "conclusionまたはcommunication_tipsの中に、本人同士の実際の様子も必ず確認する旨を"
            "1件以上含めてください。\n"
            "指定されたJSONスキーマの形式で回答してください。"
        )
        return self._generate(user_content, CompatibilityAnalysisResponse)
