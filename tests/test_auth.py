"""認証: 署名検証・許可ユーザー照合。"""
from __future__ import annotations

import base64
import hashlib
import hmac

from app.auth.line_auth import UNAUTHORIZED_MESSAGE, is_allowed_user, verify_signature


def _sign(body: bytes, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(mac).decode("utf-8")


def test_valid_signature_is_accepted():
    secret = "test-channel-secret"
    body = b'{"events":[]}'
    sig = _sign(body, secret)
    assert verify_signature(body, sig, secret) is True


def test_invalid_signature_is_rejected():
    secret = "test-channel-secret"
    body = b'{"events":[]}'
    assert verify_signature(body, "invalid-signature", secret) is False


def test_empty_signature_is_rejected():
    assert verify_signature(b"{}", "", "secret") is False


def test_tampered_body_is_rejected():
    secret = "test-channel-secret"
    sig = _sign(b'{"events":[]}', secret)
    assert verify_signature(b'{"events":[{"tampered":true}]}', sig, secret) is False


def test_allowed_user_is_recognized(allowed_user_id):
    assert is_allowed_user(allowed_user_id) is True


def test_unauthorized_user_is_rejected(allowed_user_id):
    assert is_allowed_user("Uunknownuser000000000000000000000") is False


def test_empty_user_id_is_rejected():
    assert is_allowed_user("") is False


def test_unauthorized_message_reveals_nothing():
    # 未許可ユーザーへの返信文言に、社員名・件数・機能名等の内部情報が
    # 含まれていないことを確認する。
    assert UNAUTHORIZED_MESSAGE == "このアカウントでは利用できません。"
    assert "件" not in UNAUTHORIZED_MESSAGE
    assert "エラー" not in UNAUTHORIZED_MESSAGE
