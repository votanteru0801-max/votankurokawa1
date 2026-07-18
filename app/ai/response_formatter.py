"""構造化分析結果をLINE向けの日本語テキストに整形する。"""
from __future__ import annotations

from app.ai.output_schemas import (
    DetailedAnalysisResponse,
    LabeledPoint,
    SimpleAnalysisResponse,
    TeamRecommendationResponse,
)


def _points(points: list[LabeledPoint]) -> str:
    return "\n".join(f"・【{p.label.value}】{p.text}" for p in points)


def format_simple_analysis(resp: SimpleAnalysisResponse) -> str:
    parts = [
        f"■結論\n{resp.conclusion}",
        f"■本質\n{resp.essence}",
    ]
    if resp.strengths:
        parts.append(f"■主な強み\n{_points(resp.strengths)}")
    if resp.cautions:
        parts.append(f"■注意点\n{_points(resp.cautions)}")
    if resp.current_approach:
        parts.append(f"■今の関わり方\n{_points(resp.current_approach)}")
    if resp.fortune_basis:
        parts.append("■命式上の主な根拠\n" + "\n".join(f"・【登録されている事実】{b}" for b in resp.fortune_basis))
    if resp.accuracy_notes:
        parts.append("■精度に関する注意\n" + "\n".join(f"・{n}" for n in resp.accuracy_notes))
    return "\n\n".join(parts)


def format_detailed_analysis(resp: DetailedAnalysisResponse) -> str:
    parts = [f"■結論\n{resp.conclusion}"]
    if resp.fortune_basis:
        parts.append("■命式による判断根拠\n" + "\n".join(f"・【登録されている事実】{b}" for b in resp.fortune_basis))
    parts.append(f"■中心星・日干から見た本質\n{resp.essence}")
    if resp.strengths:
        parts.append(f"■強み\n{_points(resp.strengths)}")
    if resp.weaknesses:
        parts.append(f"■弱み・注意点\n{_points(resp.weaknesses)}")
    if resp.suitable_roles:
        parts.append(f"■向いている役割\n{_points(resp.suitable_roles)}")
    if resp.current_major_luck:
        parts.append(f"■現在の大運\n{resp.current_major_luck}")
    if resp.current_annual_luck:
        parts.append(f"■現在の年運\n{resp.current_annual_luck}")
    if resp.monthly_luck:
        parts.append(f"■月運\n{resp.monthly_luck}")
    if resp.approach_and_communication:
        parts.append(f"■関わり方・伝え方\n{_points(resp.approach_and_communication)}")
    if resp.interview_questions:
        parts.append("■面談で聞く質問\n" + "\n".join(f"・{q}" for q in resp.interview_questions))
    if resp.hr_proposals:
        parts.append(f"■人事上の提案\n{_points(resp.hr_proposals)}")
    if resp.facts_to_confirm:
        parts.append("■判断前に確認すべき事実\n" + "\n".join(f"・【確認したいこと】{f}" for f in resp.facts_to_confirm))
    if resp.accuracy_notes:
        parts.append("■出生時間・データ不足などの注意\n" + "\n".join(f"・{n}" for n in resp.accuracy_notes))
    return "\n\n".join(parts)


def format_team_recommendation(resp: TeamRecommendationResponse) -> str:
    parts = [f"■条件\n{resp.criteria}"]
    if resp.recommended:
        candidate_lines = "\n\n".join(
            f"・{c.name}\n　理由: {c.reason}" for c in resp.recommended
        )
        parts.append(f"■推薦候補\n{candidate_lines}")
    else:
        parts.append("■推薦候補\n条件に合う候補が見つかりませんでした。")
    if resp.caveats:
        parts.append("■注意事項\n" + "\n".join(f"・{c}" for c in resp.caveats))
    return "\n\n".join(parts)
