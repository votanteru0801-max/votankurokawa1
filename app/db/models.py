"""PostgreSQL側モデル。会話状態・監査・キャッシュ等、人事情報の正本ではない
運用データのみを保持する（人事情報の正本はGoogleスプレッドシート）。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid_col():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class WebhookEvent(Base):
    """LINE Webhookイベントの処理履歴。イベントIDで二重処理を防止する。"""

    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = _uuid_col()
    line_event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    line_user_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    raw_payload: Mapped[dict] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="received")  # received/processing/done/error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ConversationState(Base):
    """LINEユーザーごとの会話状態（登録途中・確認待ち等のマルチターン管理）。"""

    __tablename__ = "conversation_states"

    line_user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    state_type: Mapped[str] = mapped_column(String(64), default="idle")
    state_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PendingOperation(Base):
    """確認待ちの書き込み操作（基本情報変更・削除等）。確認後に実行される。"""

    __tablename__ = "pending_operations"

    id: Mapped[uuid.UUID] = _uuid_col()
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    line_user_id: Mapped[str] = mapped_column(String(64), index=True)
    operation_type: Mapped[str] = mapped_column(String(64))  # update_basic_info/soft_delete等
    target_person_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    raw_input_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)


class ChangeHistory(Base):
    """すべての登録・更新・削除操作の変更履歴。取り消しの基礎データ。"""

    __tablename__ = "change_history"

    id: Mapped[uuid.UUID] = _uuid_col()
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    actor_line_user_id: Mapped[str] = mapped_column(String(64))
    target_person_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    operation_type: Mapped[str] = mapped_column(String(64))  # register/update/interview_note/soft_delete/undo
    field_changes: Mapped[dict] = mapped_column(JSONB, default=dict)  # {field: {"before":..,"after":..}}
    before_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_input_text: Mapped[str] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[str] = mapped_column(String(32), default="success")  # success/failed
    undo_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    undone: Mapped[bool] = mapped_column(Boolean, default=False)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PersonIndexCache(Base):
    """Googleスプレッドシート（正本）から同期した検索用キャッシュ。
    正本ではないため、書き込みは必ずSheets側が成功した後に反映する。
    """

    __tablename__ = "person_index_cache"

    person_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128), index=True)
    kana: Mapped[str] = mapped_column(String(128), default="")
    category: Mapped[str] = mapped_column(String(32), index=True)
    birth_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    department: Mapped[str] = mapped_column(String(128), default="")
    position: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(64), default="")
    sheet_row_ref: Mapped[str] = mapped_column(String(64), default="")
    deletion_status: Mapped[str] = mapped_column(String(32), default="active")
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class CalculationCache(Base):
    """命式計算結果のキャッシュ。同一入力・同一ポリシーバージョンなら再計算しない。"""

    __tablename__ = "calculation_cache"

    id: Mapped[uuid.UUID] = _uuid_col()
    person_id: Mapped[str] = mapped_column(String(64), index=True)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    policy_version: Mapped[str] = mapped_column(String(32))
    engine: Mapped[str] = mapped_column(String(32))  # shichuu_suimei / sanmeigaku / luck_cycles
    result_json: Mapped[dict] = mapped_column(JSONB)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AIRequestLog(Base):
    """Claude APIへのリクエストのメタデータ。プロンプト本文の機微情報は記録しない。"""

    __tablename__ = "ai_request_log"

    id: Mapped[uuid.UUID] = _uuid_col()
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    line_user_id: Mapped[str] = mapped_column(String(64))
    intent: Mapped[str] = mapped_column(String(64), default="")
    tool_calls: Mapped[dict] = mapped_column(JSONB, default=dict)
    data_sent_summary: Mapped[dict] = mapped_column(JSONB, default=dict)  # 送信した「項目名」のみ記録
    model: Mapped[str] = mapped_column(String(64), default="")
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="success")


class ErrorLog(Base):
    """エラー記録。スタックトレース等の内部情報はここに保存し、LINEには出さない。"""

    __tablename__ = "error_log"

    id: Mapped[uuid.UUID] = _uuid_col()
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    component: Mapped[str] = mapped_column(String(64))
    error_type: Mapped[str] = mapped_column(String(128))
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    line_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
