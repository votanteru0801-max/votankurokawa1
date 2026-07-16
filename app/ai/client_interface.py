"""AI分析クライアントの抽象インターフェース。本番(Anthropic)とモックを差し替え可能にする。

MVPでは「データ取得・最小化はアプリ側が確定させ、Claudeには労を集約した最終解釈の
生成のみを依頼する」設計を採用する（Claudeがperson_idを取り違える等のリスクを避け、
書き込みだけでなく読み取りの対象特定もアプリ側で確実に行うため）。
一方で app/ai/tools.py・tool_executor.py は要件24章の「ツールまたは同等の機能」を
満たす完全なツール実行層として用意しており、より複雑な自由対話（比較・チーム編成等、
第2段階）ではClaudeによる能動的なツール呼び出しループへ拡張できる。
"""
from __future__ import annotations

from typing import Literal, Protocol, Union

from app.ai.output_schemas import DetailedAnalysisResponse, SimpleAnalysisResponse

AnalysisMode = Literal["simple", "detailed"]


class AIAnalysisClient(Protocol):
    def generate_analysis(
        self,
        mode: AnalysisMode,
        person_name: str,
        person_id: str,
        calculation_data: dict,
        hr_context: dict,
        question: str,
        accuracy_notes: list[str],
    ) -> Union[SimpleAnalysisResponse, DetailedAnalysisResponse]:
        ...


class AnalysisGenerationError(Exception):
    pass
