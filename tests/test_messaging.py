"""LINEメッセージ分割ユーティリティのテスト（DB不要）。"""
from __future__ import annotations

from app.config import LineLimits
from app.line.messaging import prepare_reply_messages, split_message


def test_short_message_is_not_split():
    text = "短いメッセージです。"
    assert split_message(text) == [text]


def test_long_message_is_split_within_limit():
    text = "\n\n".join([f"■セクション{i}\n" + "あ" * 500 for i in range(10)])
    chunks = split_message(text)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= LineLimits.SAFE_CHUNK_LENGTH


def test_prepare_reply_messages_respects_max_count():
    text = "\n\n".join([f"■セクション{i}\n" + "あ" * 1700 for i in range(10)])
    chunks = prepare_reply_messages(text)
    assert len(chunks) <= LineLimits.MAX_MESSAGES_PER_REPLY
