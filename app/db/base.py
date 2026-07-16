"""SQLAlchemyのベース定義・エンジン・セッション。"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def get_engine():
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


_engine = None
_SessionLocal = None


def _ensure_session_factory():
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine = get_engine()
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _SessionLocal


def get_session() -> Generator[Session, None, None]:
    session_factory = _ensure_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
