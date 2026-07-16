"""初期スキーマ: 会話状態・監査・キャッシュ関連テーブル

Revision ID: 0001
Revises:
Create Date: 2026-07-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("line_event_id", sa.String(128), nullable=False, unique=True),
        sa.Column("line_user_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("raw_payload", pg.JSONB, nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="received"),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index("ix_webhook_events_line_user_id", "webhook_events", ["line_user_id"])
    op.create_index("ix_webhook_events_line_event_id", "webhook_events", ["line_event_id"], unique=True)

    op.create_table(
        "conversation_states",
        sa.Column("line_user_id", sa.String(64), primary_key=True),
        sa.Column("state_type", sa.String(64), nullable=False, server_default="idle"),
        sa.Column("state_data", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "pending_operations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("line_user_id", sa.String(64), nullable=False),
        sa.Column("operation_type", sa.String(64), nullable=False),
        sa.Column("target_person_id", sa.String(64), nullable=True),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.Column("raw_input_text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("executed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("cancelled", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_pending_operations_line_user_id", "pending_operations", ["line_user_id"])

    op.create_table(
        "change_history",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_line_user_id", sa.String(64), nullable=False),
        sa.Column("target_person_id", sa.String(64), nullable=True),
        sa.Column("operation_type", sa.String(64), nullable=False),
        sa.Column("field_changes", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("before_snapshot", pg.JSONB, nullable=True),
        sa.Column("after_snapshot", pg.JSONB, nullable=True),
        sa.Column("raw_input_text", sa.Text, nullable=False),
        sa.Column("confirmed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("result", sa.String(32), nullable=False, server_default="success"),
        sa.Column("undo_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("undone", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_change_history_target_person_id", "change_history", ["target_person_id"])

    op.create_table(
        "person_index_cache",
        sa.Column("person_id", sa.String(64), primary_key=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("kana", sa.String(128), nullable=False, server_default=""),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("birth_date", sa.String(10), nullable=True),
        sa.Column("department", sa.String(128), nullable=False, server_default=""),
        sa.Column("position", sa.String(128), nullable=False, server_default=""),
        sa.Column("status", sa.String(64), nullable=False, server_default=""),
        sa.Column("sheet_row_ref", sa.String(64), nullable=False, server_default=""),
        sa.Column("deletion_status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_person_index_cache_display_name", "person_index_cache", ["display_name"])
    op.create_index("ix_person_index_cache_category", "person_index_cache", ["category"])

    op.create_table(
        "calculation_cache",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", sa.String(64), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("engine", sa.String(32), nullable=False),
        sa.Column("result_json", pg.JSONB, nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_calculation_cache_person_id", "calculation_cache", ["person_id"])
    op.create_index("ix_calculation_cache_input_hash", "calculation_cache", ["input_hash"])

    op.create_table(
        "ai_request_log",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("line_user_id", sa.String(64), nullable=False),
        sa.Column("intent", sa.String(64), nullable=False, server_default=""),
        sa.Column("tool_calls", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("data_sent_summary", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("model", sa.String(64), nullable=False, server_default=""),
        sa.Column("tokens_in", sa.Integer, nullable=True),
        sa.Column("tokens_out", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="success"),
    )

    op.create_table(
        "error_log",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("component", sa.String(64), nullable=False),
        sa.Column("error_type", sa.String(128), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("context", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("line_user_id", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("error_log")
    op.drop_table("ai_request_log")
    op.drop_table("calculation_cache")
    op.drop_table("person_index_cache")
    op.drop_table("change_history")
    op.drop_table("pending_operations")
    op.drop_table("conversation_states")
    op.drop_table("webhook_events")
