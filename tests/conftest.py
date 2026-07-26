"""pytest共通フィクスチャ。

運用データの保存先はGoogle Firestore。テストではFirestoreエミュレータ
（docker-compose.test.ymlが用意する firestore-emulator コンテナ）を使う。
ローカル実行手順:
    docker compose -f docker-compose.yml -f docker-compose.test.yml up -d firestore-emulator
    pytest
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("LINE_MODE", "mock")
os.environ.setdefault("GOOGLE_SHEETS_MODE", "mock")
os.environ.setdefault("ANTHROPIC_MODE", "mock")
os.environ.setdefault("ALLOWED_LINE_USER_ID", "Uauthorizeduser0000000000000000")
os.environ.setdefault(
    "FIRESTORE_EMULATOR_HOST", os.environ.get("TEST_FIRESTORE_EMULATOR_HOST", "localhost:8082")
)
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("LINE_CHANNEL_SECRET", "test-channel-secret")

_CLEARED_COLLECTIONS = (
    "conversation_states",
    "webhook_events",
    "change_history",
    "ai_request_log",
    "error_log",
)


@pytest.fixture(scope="session")
def db_engine():
    from app.config import get_settings
    from app.db.base import get_firestore_client

    get_settings.cache_clear()
    client = get_firestore_client()
    yield client


@pytest.fixture()
def db_session(db_engine):
    yield db_engine
    # テスト間の独立性を保つため、このテストで使ったコレクションをクリアする
    # （Firestoreエミュレータは自動リセットされないため）。
    for collection_name in _CLEARED_COLLECTIONS:
        for doc in db_engine.collection(collection_name).stream():
            doc.reference.delete()


@pytest.fixture()
def repo():
    from app.sheets.mock_repository import MockPersonRepository

    return MockPersonRepository()


@pytest.fixture()
def ai_client():
    from app.ai.mock_client import MockAIClient

    return MockAIClient()


@pytest.fixture()
def orchestrator(db_session, repo, ai_client):
    from app.ai.orchestrator import Orchestrator

    return Orchestrator(db_session, repo, ai_client)


@pytest.fixture()
def allowed_user_id():
    from app.config import get_settings

    return get_settings().allowed_line_user_id
