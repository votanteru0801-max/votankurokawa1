"""冪等性キー生成。LINEイベントIDを基本とし、同一操作の二重実行を防ぐ。"""
from __future__ import annotations


def idempotency_key(line_event_id: str, operation_type: str) -> str:
    return f"{line_event_id}:{operation_type}"
