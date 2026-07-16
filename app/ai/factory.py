"""設定に応じてAIクライアント(本番/モック)を返すファクトリ。"""
from __future__ import annotations

from app.config import get_settings


def get_ai_client():
    settings = get_settings()
    if settings.anthropic_mode.value == "live":
        from app.ai.real_client import AnthropicAIClient

        return AnthropicAIClient()
    from app.ai.mock_client import MockAIClient

    return MockAIClient()
