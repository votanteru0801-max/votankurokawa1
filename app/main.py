"""FastAPIエントリポイント。"""
from __future__ import annotations

import structlog
from fastapi import FastAPI

from app.config import get_settings
from app.line.webhook import router as line_webhook_router

logger = structlog.get_logger()

app = FastAPI(title="黒革の手帳", description="石橋輝一専用 人事分析LINE Bot", version="0.1.0")
app.include_router(line_webhook_router)


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "line_mode": settings.line_mode.value,
        "google_sheets_mode": settings.google_sheets_mode.value,
        "anthropic_mode": settings.anthropic_mode.value,
    }


@app.on_event("startup")
def on_startup() -> None:
    settings = get_settings()
    logger.info(
        "kuroeda_techo_startup",
        app_env=settings.app_env,
        line_mode=settings.line_mode.value,
        google_sheets_mode=settings.google_sheets_mode.value,
        anthropic_mode=settings.anthropic_mode.value,
    )
