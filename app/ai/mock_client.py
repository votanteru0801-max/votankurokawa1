"""ローカル開発・自動テスト用のモックAIクライアント。
Anthropic APIキーが無くても分析生成フロー全体（データ取得→最小化→構造化応答→
LINE分割送信）を検証できるようにする。命式データは本物の計算エンジンの結果を
そのまま使い、"AIによる人事仮説"部分のみ規則ベースの簡易文言で埋める。
"""
from __future__ import annotations

from app.ai.output_schemas import (
    DetailedAnalysisResponse,
    Label,
    LabeledPoint,
    SimpleAnalysisResponse,
    TeamCandidate,
    TeamRecommendationResponse,
)


def _fortune_basis_lines(calculation_data: dict) -> list[str]:
    fp = calculation_data.get("shichuu_suimei", {})
    lines = []
    if fp:
        yp, mp, dp = fp.get("year_pillar"), fp.get("month_pillar"), fp.get("day_pillar")
        if yp and mp and dp:
            lines.append(f"四柱: 年柱{yp['stem']}{yp['branch']} / 月柱{mp['stem']}{mp['branch']} / 日柱{dp['stem']}{dp['branch']}")
        hp = fp.get("hour_pillar")
        if hp:
            lines.append(f"時柱: {hp['stem']}{hp['branch']}")
        elif fp.get("hour_pillar_omitted_reason"):
            lines.append(fp["hour_pillar_omitted_reason"])
        lines.append(f"日干: {fp.get('day_master_stem')}（{fp.get('day_master_element')}）")
    sm = calculation_data.get("sanmeigaku", {})
    if sm and sm.get("center_star"):
        lines.append(f"中心星: {sm['center_star']}（検証状況: {sm.get('center_star_confidence')}）")
    return lines


class MockAIClient:
    def generate_analysis(
        self,
        mode: str,
        person_name: str,
        person_id: str,
        calculation_data: dict,
        hr_context: dict,
        question: str,
        accuracy_notes: list[str],
    ):
        basis = _fortune_basis_lines(calculation_data)
        day_master = calculation_data.get("shichuu_suimei", {}).get("day_master_element", "不明")
        center_star = calculation_data.get("sanmeigaku", {}).get("center_star", "不明")

        strengths = [
            LabeledPoint(
                label=Label.FORTUNE_TRAIT,
                text=f"日干の五行が{day_master}であり、中心星が{center_star}であることから、一定の行動特性の傾向がうかがえます。",
            ),
        ]
        cautions = [
            LabeledPoint(
                label=Label.AI_HYPOTHESIS,
                text="これは簡易モック応答です。実運用ではAnthropic APIキー設定後、より具体的な人事仮説が生成されます。",
            ),
        ]

        if mode == "simple":
            return SimpleAnalysisResponse(
                person_id=person_id,
                conclusion=f"{person_name}さんについて、命式データに基づく簡易分析結果です（モック応答）。",
                essence=f"日干{day_master} / 中心星{center_star}を中心とした人物傾向です。",
                strengths=strengths,
                cautions=cautions,
                current_approach=[
                    LabeledPoint(label=Label.PROPOSAL, text="まずは1on1で本人の状況をヒアリングすることをおすすめします。")
                ],
                fortune_basis=basis,
                accuracy_notes=accuracy_notes,
            )

        return DetailedAnalysisResponse(
            person_id=person_id,
            conclusion=f"{person_name}さんについて、命式データと登録情報に基づく詳細分析です（モック応答）。",
            fortune_basis=basis,
            essence=f"日干{day_master} / 中心星{center_star}を中心とした人物傾向です。",
            strengths=strengths,
            weaknesses=[
                LabeledPoint(label=Label.AI_HYPOTHESIS, text="モック応答のため弱み分析は簡略化されています。")
            ],
            suitable_roles=[LabeledPoint(label=Label.AI_HYPOTHESIS, text="実運用でより具体的な役割提案が生成されます。")],
            current_major_luck=str(calculation_data.get("luck_cycles", {}).get("direction", "")),
            current_annual_luck="",
            approach_and_communication=[
                LabeledPoint(label=Label.PROPOSAL, text="定期的な1on1でキャリア希望を確認してください。")
            ],
            interview_questions=["最近の業務で手応えを感じた場面はありますか？"],
            hr_proposals=[LabeledPoint(label=Label.PROPOSAL, text="次回評価面談で希望キャリアを再確認してください。")],
            facts_to_confirm=["登録されている所属・役職が最新かどうか"],
            accuracy_notes=accuracy_notes,
        )

    def recommend_team(self, criteria: str, candidates: list[dict]) -> TeamRecommendationResponse:
        picked = candidates[:3]
        return TeamRecommendationResponse(
            criteria=criteria,
            recommended=[
                TeamCandidate(
                    name=c.get("氏名") or c.get("name", "?"),
                    reason=(
                        f"モック応答: 年齢{c.get('年齢', '不明')}・日主{c.get('日主', '?')}・"
                        f"中心星{c.get('中心星') or '不明'}のため（実運用ではより具体的な理由が生成されます）。"
                    ),
                )
                for c in picked
            ],
            caveats=["これはモック応答です。占術だけで採用・配置を決定せず、本人の意向や実績も必ず確認してください。"],
        )
