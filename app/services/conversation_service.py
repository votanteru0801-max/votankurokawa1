"""LINEユーザーごとの会話状態（登録途中・確認待ち等）の永続化。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import ConversationState


def get_state(db: Session, line_user_id: str) -> ConversationState:
    state = db.get(ConversationState, line_user_id)
    if state is None:
        state = ConversationState(line_user_id=line_user_id, state_type="idle", state_data={})
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def set_state(db: Session, line_user_id: str, state_type: str, state_data: dict) -> None:
    state = get_state(db, line_user_id)
    state.state_type = state_type
    state.state_data = state_data
    state.updated_at = datetime.utcnow()
    db.add(state)
    db.commit()


def clear_state(db: Session, line_user_id: str) -> None:
    set_state(db, line_user_id, "idle", {})
