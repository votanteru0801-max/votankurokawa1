"""監査ログ・AIリクエストメタデータ・エラー記録のヘルパー。
機微情報の本文はここには保存しない（フィールド名のみ等の要約情報にとどめる）。

Firestore版。"ai_request_log" / "error_log" コレクションに追記のみ行う
（アプリ内から読み返す処理は無いため、クエリ・インデックスは不要）。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


def log_ai_request(
    db,
    line_user_id: str,
    intent: str,
    tool_calls: dict,
    data_sent_summary: dict,
    model: str,
    status: str = "success",
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    latency_ms: int | None = None,
) -> None:
    db.collection("ai_request_log").document(str(uuid.uuid4())).set(
        {
            "occurred_at": datetime.now(timezone.utc),
            "line_user_id": line_user_id,
            "intent": intent,
            "tool_calls": tool_calls,
            "data_sent_summary": data_sent_summary,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "status": status,
        }
    )


def log_error(
    db,
    component: str,
    error_type: str,
    message: str,
    context: dict | None = None,
    line_user_id: str | None = None,
) -> None:
    db.collection("error_log").document(str(uuid.uuid4())).set(
        {
            "occurred_at": datetime.now(timezone.utc),
            "component": component,
            "error_type": error_type,
            "message": message,
            "context": context or {},
            "line_user_id": line_user_id,
        }
    )
