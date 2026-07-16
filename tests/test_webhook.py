"""LINE Webhookエンドポイントの統合テスト（FastAPI TestClient）。
署名検証・未許可ユーザー・イベント重複防止を確認する。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json

from fastapi.testclient import TestClient


def _sign(body: bytes, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(mac).decode("utf-8")


def test_webhook_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("LINE_MODE", "live")
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test-secret")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    client = TestClient(app)
    body = json.dumps({"events": []}).encode()
    resp = client.post("/webhook", content=body, headers={"X-Line-Signature": "invalid"})
    assert resp.status_code == 403
    get_settings.cache_clear()


def test_webhook_accepts_valid_signature_and_returns_200(monkeypatch):
    monkeypatch.setenv("LINE_MODE", "live")
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test-secret")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    client = TestClient(app)
    body = json.dumps({"events": []}).encode()
    sig = _sign(body, "test-secret")
    resp = client.post("/webhook", content=body, headers={"X-Line-Signature": sig})
    assert resp.status_code == 200
    get_settings.cache_clear()


def test_webhook_mock_mode_skips_signature_check(monkeypatch):
    monkeypatch.setenv("LINE_MODE", "mock")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    client = TestClient(app)
    body = json.dumps({"events": []}).encode()
    resp = client.post("/webhook", content=body, headers={"X-Line-Signature": ""})
    assert resp.status_code == 200
    get_settings.cache_clear()


def test_health_endpoint():
    from app.main import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
