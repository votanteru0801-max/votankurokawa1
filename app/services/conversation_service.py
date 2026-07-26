"""LINEユーザーごとの会話状態（登録途中・確認待ち等）の永続化。

Firestore版。コレクション "conversation_states" に、line_user_id を
ドキュメントIDとして1ユーザー1ドキュメントで保持する。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

COLLECTION = "conversation_states"
DEFAULT_STATE_TYPE = "idle"


@dataclass
class ConversationState:
    line_user_id: str
    state_type: str = DEFAULT_STATE_TYPE
    state_data: dict[str, Any] = field(default_factory=dict)


def get_state(db, line_user_id: str) -> ConversationState:
    doc = db.collection(COLLECTION).document(line_user_id).get()
    if not doc.exists:
        return ConversationState(line_user_id=line_user_id)
    data = doc.to_dict() or {}
    return ConversationState(
        line_user_id=line_user_id,
        state_type=data.get("state_type", DEFAULT_STATE_TYPE),
        state_data=data.get("state_data", {}),
    )


def set_state(db, line_user_id: str, state_type: str, state_data: dict) -> None:
    db.collection(COLLECTION).document(line_user_id).set(
        {
            "state_type": state_type,
            "state_data": state_data,
            "updated_at": datetime.now(timezone.utc),
        }
    )


def clear_state(db, line_user_id: str) -> None:
    set_state(db, line_user_id, DEFAULT_STATE_TYPE, {})
