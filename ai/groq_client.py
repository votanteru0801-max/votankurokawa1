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
from app.ai.output_schemas import (
    CompatibilityAnalysisResponse,
    DetailedAnalysisResponse,
    SimpleAnalysisResponse,
    TeamRecommendationResponse,
)
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

    def _call_tool(self, tool_name: str, tool_schema: dict, user_content: str, schema_cls, max_tokens: int = 3500):
        """強制tool_choiceでツールを呼び出し、JSONを検証・パースするまで再試行する共通処理。"""
        tool = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": "結果を指定スキーマで構造化して提出する。",
                "parameters": tool_schema,
            },
        }
        client = self._get_client()
        last_error: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    tools=[tool],
                    tool_choice={"type": "function", "function": {"name": tool_name}},
                    # 無料枠のTPM(1分あたりトークン数)上限が低いモデルのため、
                    # 入力+出力の合計が収まるよう控えめな値にしている
                    # （呼び出し元ごとに必要最小限の値を渡す）。
                    max_tokens=max_tokens,
                    # openai/gpt-oss系は内部の思考(reasoning)にもトークンを使うため、
                    # 効果を「低」にして、その分をツール呼び出し自体に回す。
                    # これを指定しないと、思考だけでmax_tokensを使い切ってしまい
                    # 「Tool choice is required, but model did not call a tool」という
                    # エラーになることがある。
                    extra_body={"reasoning_effort": "low"},
                )
            except Exception as e:  # Groq側のツール呼び出し検証エラー(400)等もここで捕捉して再試行する
                last_error = e
                print(f"[AI_DEBUG] {tool_name}: API呼び出しエラー: {e!r}")
                continue
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
            if not tool_calls:
                last_error = AnalysisGenerationError("AIがツールを呼び出しませんでした。")
                print(f"[AI_DEBUG] {tool_name}: ツール未呼び出し。content={message.content!r}")
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
                print(f"[AI_DEBUG] {tool_name}: 解析/検証エラー: {e!r} raw_args={raw_args!r}")
                continue
        print(f"[AI_DEBUG] {tool_name}: 全リトライ失敗。last_error={last_error!r}")
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
            "回答本文に書かないでください。リストに無ければ、その項目は登録済み・算出済みです。\n\n"
            "重要（出力形式）: strengths/cautions/current_approach 等の各要素は、"
            "必ず {\"label\": ..., \"text\": ...} の2つのキーだけを持つオブジェクトにしてください。"
            "\"point\"のような別名のキーは使わないでください。"
            "labelには次の5つの文字列のうちいずれか1つだけを正確にそのまま使ってください: "
            "\"登録されている事実\", \"命式上の傾向\", \"AIによる人事仮説\", \"確認したいこと\", \"提案\"。\n"
            "重要（強み・弱みの書き方）: strengths（強み）は命式・大運等の裏付けを添えて必ず記入してください。"
            "weaknesses/cautions（弱み・注意点）は、大運・年運・十二運などに際立った弱みの兆候が"
            "明確に見当たる場合のみ記入し、そうでなければ無理に弱みを作り出さず空のままにしてください。"
            "growth_guidanceには、強みや伸びどき（十二運が長生・冠帯・建禄・帝旺にあたる時期）を踏まえた、"
            "この人物の具体的な伸ばし方・関わり方を記入してください。"
            "risk_notesには、この人物が業務上起こしやすいミス・エラーの傾向や、"
            "他のスタッフとの間で衝突・すれ違いが起きやすい傾向を、命式上の根拠とともに具体的に"
            "記入してください（根拠が乏しければ無理に作り出さず空のままでよい）。\n"
            + detail_instruction + kubou_instruction +
            "submit_analysisツールを使って回答を構造化して提出してください。"
        )
        return self._call_tool(
            "submit_analysis", schema_cls.model_json_schema(), user_content, schema_cls,
            max_tokens=6000 if mode == "detailed" else 3500,
        )

    def recommend_team(self, criteria: str, candidates: list[dict]) -> TeamRecommendationResponse:
        # 無料枠のTPM上限に収めるため、候補者一覧はラベル無しのCSV形式にして
        # トークン数を抑える（候補者数が多い場合ほど効果が大きい）。
        # フィールド構成は呼び出し元（簡易版/詳細版）によって異なる。
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
            "recommend_team",
            TeamRecommendationResponse.model_json_schema(),
            user_content,
            TeamRecommendationResponse,
            max_tokens=1800,
        )

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
            "重要（出力形式）: good_points/friction_points/communication_tips の各要素は、"
            "必ず {\"label\": ..., \"text\": ...} の2つのキーだけを持つオブジェクトにしてください。"
            "labelには次の5つの文字列のうちいずれか1つだけを正確にそのまま使ってください: "
            "\"登録されている事実\", \"命式上の傾向\", \"AIによる人事仮説\", \"確認したいこと\", \"提案\"。\n"
            "重要（良い点・注意点の書き方）: good_points（相性の良い点）は命式の裏付けを添えて"
            "必ず1件以上記入してください。friction_points（注意したいすれ違いポイント）は、"
            "命式から明確な根拠が見つかる場合のみ記入し、無理に作り出さないでください。\n"
            "重要: 相性だけで人事配置・評価・採用可否を自動的に決定しないよう、"
            "conclusionまたはcommunication_tipsの中に、本人同士の実際の様子も必ず確認する旨を"
            "1件以上含めてください。\n"
            "submit_compatibilityツールを使って回答を構造化して提出してください。"
        )
        return self._call_tool(
            "submit_compatibility",
            CompatibilityAnalysisResponse.model_json_schema(),
            user_content,
            CompatibilityAnalysisResponse,
            max_tokens=4500,
        )
