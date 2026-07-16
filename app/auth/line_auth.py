"""LINE Webhook署名検証と許可ユーザー照合。"""
from __future__ import annotations

import base64
import hashlib
import hmac

from app.config import get_settings

UNAUTHORIZED_MESSAGE = "このアカウントでは利用できません。"


def verify_signature(body: bytes, signature: str, channel_secret: str) -> bool:
    """LINE Webhookの署名検証（HMAC-SHA256 + Base64）。"""
    if not channel_secret or not signature:
        return False
    mac = hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def is_allowed_user(line_user_id: str) -> bool:
    settings = get_settings()
    return bool(line_user_id) and line_user_id == settings.allowed_line_user_id
