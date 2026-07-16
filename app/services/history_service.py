"""変更履歴の記録と取り消し（undo）。"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import ChangeHistory
from app.sheets.interface import PersonRepository


class UndoNotAvailableError(Exception):
    pass


def record_change(
    db: Session,
    actor_line_user_id: str,
    target_person_id: str | None,
    operation_type: str,
    field_changes: dict,
    before_snapshot: dict | None,
    after_snapshot: dict | None,
    raw_input_text: str,
    confirmed: bool,
    result: str = "success",
) -> ChangeHistory:
    settings = get_settings()
    now = datetime.utcnow()
    entry = ChangeHistory(
        id=uuid.uuid4(),
        occurred_at=now,
        actor_line_user_id=actor_line_user_id,
        target_person_id=target_person_id,
        operation_type=operation_type,
        field_changes=field_changes,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        raw_input_text=raw_input_text,
        confirmed=confirmed,
        result=result,
        undo_deadline=now + timedelta(minutes=settings.undo_window_minutes),
        undone=False,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_last_undoable_change(
    db: Session, actor_line_user_id: str, target_person_id: str | None = None
) -> ChangeHistory | None:
    stmt = (
        select(ChangeHistory)
        .where(
            ChangeHistory.actor_line_user_id == actor_line_user_id,
            ChangeHistory.undone.is_(False),
            ChangeHistory.result == "success",
            ChangeHistory.undo_deadline > datetime.utcnow(),
        )
        .order_by(ChangeHistory.occurred_at.desc())
    )
    if target_person_id:
        stmt = stmt.where(ChangeHistory.target_person_id == target_person_id)
    return db.execute(stmt).scalars().first()


def undo_last_change(
    db: Session, repo: PersonRepository, actor_line_user_id: str, target_person_id: str | None = None
) -> ChangeHistory:
    change = get_last_undoable_change(db, actor_line_user_id, target_person_id)
    if change is None:
        raise UndoNotAvailableError("取り消せる操作がありません（期限切れ、または対象がない可能性があります）。")

    person_id = change.target_person_id
    if change.operation_type == "register":
        repo.soft_delete(uuid.UUID(person_id))
    elif change.operation_type == "update_basic_info":
        before_values = {k: v["before"] for k, v in change.field_changes.items()}
        repo.update_person_fields(uuid.UUID(person_id), before_values)
    elif change.operation_type == "interview_note":
        repo.remove_last_interview_note(uuid.UUID(person_id))
    elif change.operation_type == "soft_delete":
        repo.restore(uuid.UUID(person_id))
    else:
        raise UndoNotAvailableError(f"操作種別'{change.operation_type}'は取り消しに対応していません。")

    change.undone = True
    change.undone_at = datetime.utcnow()
    db.add(change)
    db.commit()
    db.refresh(change)
    return change
