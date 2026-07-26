"""変更履歴の記録と取り消し（undo）。

Firestore版。"change_history" コレクションに1操作1ドキュメントで保存する。
取り消し可能な直近の操作を探す処理（get_last_undoable_change）は、
Firestoreの複合インデックス要件を避けるため、等価条件（actor/undone/result）
のみをクエリで絞り込み、期限切れ判定(undo_deadline)と対象人物の絞り込みは
アプリ側でループして行う（直近20件のみ見れば十分なため、性能上も問題ない）。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from google.cloud import firestore

from app.config import get_settings
from app.sheets.interface import PersonRepository

COLLECTION = "change_history"


class UndoNotAvailableError(Exception):
    pass


@dataclass
class ChangeHistoryEntry:
    id: str
    occurred_at: datetime
    actor_line_user_id: str
    target_person_id: str | None
    operation_type: str
    field_changes: dict
    before_snapshot: dict | None
    after_snapshot: dict | None
    raw_input_text: str
    confirmed: bool
    result: str
    undo_deadline: datetime | None
    undone: bool
    undone_at: datetime | None = None


def _doc_to_entry(doc) -> ChangeHistoryEntry:
    data = doc.to_dict() or {}
    return ChangeHistoryEntry(
        id=doc.id,
        occurred_at=data.get("occurred_at"),
        actor_line_user_id=data.get("actor_line_user_id", ""),
        target_person_id=data.get("target_person_id"),
        operation_type=data.get("operation_type", ""),
        field_changes=data.get("field_changes", {}),
        before_snapshot=data.get("before_snapshot"),
        after_snapshot=data.get("after_snapshot"),
        raw_input_text=data.get("raw_input_text", ""),
        confirmed=data.get("confirmed", False),
        result=data.get("result", "success"),
        undo_deadline=data.get("undo_deadline"),
        undone=data.get("undone", False),
        undone_at=data.get("undone_at"),
    )


def record_change(
    db,
    actor_line_user_id: str,
    target_person_id: str | None,
    operation_type: str,
    field_changes: dict,
    before_snapshot: dict | None,
    after_snapshot: dict | None,
    raw_input_text: str,
    confirmed: bool,
    result: str = "success",
) -> ChangeHistoryEntry:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    undo_deadline = now + timedelta(minutes=settings.undo_window_minutes)
    entry_id = str(uuid.uuid4())
    db.collection(COLLECTION).document(entry_id).set(
        {
            "occurred_at": now,
            "actor_line_user_id": actor_line_user_id,
            "target_person_id": target_person_id,
            "operation_type": operation_type,
            "field_changes": field_changes,
            "before_snapshot": before_snapshot,
            "after_snapshot": after_snapshot,
            "raw_input_text": raw_input_text,
            "confirmed": confirmed,
            "result": result,
            "undo_deadline": undo_deadline,
            "undone": False,
            "undone_at": None,
        }
    )
    return ChangeHistoryEntry(
        id=entry_id,
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
        undo_deadline=undo_deadline,
        undone=False,
        undone_at=None,
    )


def get_last_undoable_change(
    db, actor_line_user_id: str, target_person_id: str | None = None
) -> ChangeHistoryEntry | None:
    query = (
        db.collection(COLLECTION)
        .where("actor_line_user_id", "==", actor_line_user_id)
        .where("undone", "==", False)
        .where("result", "==", "success")
        .order_by("occurred_at", direction=firestore.Query.DESCENDING)
        .limit(20)
    )
    now = datetime.now(timezone.utc)
    for doc in query.stream():
        entry = _doc_to_entry(doc)
        if entry.undo_deadline is not None and entry.undo_deadline <= now:
            continue
        if target_person_id and entry.target_person_id != target_person_id:
            continue
        return entry
    return None


def undo_last_change(
    db, repo: PersonRepository, actor_line_user_id: str, target_person_id: str | None = None
) -> ChangeHistoryEntry:
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

    undone_at = datetime.now(timezone.utc)
    db.collection(COLLECTION).document(change.id).update({"undone": True, "undone_at": undone_at})
    change.undone = True
    change.undone_at = undone_at
    return change
