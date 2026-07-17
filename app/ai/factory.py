"""設定に応じてAIクライアント(本番/モック)を返すファクトリ。"""
from __future__ import annotations

from app.config import get_settings


def get_ai_client():
    settings = get_settings()
    provider = settings.ai_provider
    if provider == "mock" and settings.anthropic_mode.value == "live":
        # 後方互換: ai_providerを設定せずANTHROPIC_MODE=liveだけにしていた場合。
        provider = "anthropic"

    if provider == "anthropic":
        from app.ai.real_client import AnthropicAIClient

        return AnthropicAIClient()
    if provider == "gemini":
        from app.ai.gemini_client import GeminiAIClient

        return GeminiAIClient()
    from app.ai.mock_client import MockAIClient

    return MockAIClient()
