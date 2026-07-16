"""監査ログ・AIリクエストメタデータ・エラー記録のヘルパー。
機微情報の本文はここには保存しない（フィールド名のみ等の要約情報にとどめる）。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import AIRequestLog, ErrorLog


def log_ai_request(
    db: Session,
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
    db.add(
        AIRequestLog(
            id=uuid.uuid4(),
            occurred_at=datetime.utcnow(),
            line_user_id=line_user_id,
            intent=intent,
            tool_calls=tool_calls,
            data_sent_summary=data_sent_summary,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            status=status,
        )
    )
    db.commit()


def log_error(
    db: Session, component: str, error_type: str, message: str, context: dict | None = None,
    line_user_id: str | None = None,
) -> None:
    db.add(
        ErrorLog(
            id=uuid.uuid4(),
            occurred_at=datetime.utcnow(),
            component=component,
            error_type=error_type,
            message=message,
            context=context or {},
            line_user_id=line_user_id,
        )
    )
    db.commit()
