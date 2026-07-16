"""pytest共通フィクスチャ。

DBを使うテストはPostgreSQL（docker-compose上のkuroeda-db、またはCIのPostgres
サービスコンテナ）を前提とする。app/db/models.py がPostgreSQL固有の型
（JSONB等）を使用しているため、SQLiteでは代替できない。
ローカル実行手順:
    docker compose up -d db
    alembic upgrade head
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
    "DATABASE_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://kuroeda:kuroeda@localhost:5432/kuroeda_test"),
)
os.environ.setdefault("LINE_CHANNEL_SECRET", "test-channel-secret")


@pytest.fixture(scope="session")
def db_engine():
    from sqlalchemy import create_engine

    from app.config import get_settings
    from app.db.base import Base

    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, future=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine):
    from sqlalchemy.orm import sessionmaker

    session_factory = sessionmaker(bind=db_engine, future=True)
    session = session_factory()
    yield session
    session.rollback()
    # テスト間の独立性を保つため主要テーブルをクリアする
    from app.db import models

    for table in reversed(models.Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


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
