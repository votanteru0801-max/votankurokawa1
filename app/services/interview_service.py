"""面談記録の追記・削除。追記は確認なしで保存し、上書きせず日付ごとに追加する。"""
from __future__ import annotations

from datetime import date

from app.schemas.person import Person, SensitiveTag
from app.services import history_service
from app.sheets.interface import PersonRepository


def append_note(
    repo: PersonRepository,
    db,
    actor_line_user_id: str,
    person: Person,
    content: str,
    occurred_on: date,
    sensitive_tags: list[SensitiveTag],
    raw_input_text: str,
) -> Person:
    updated = repo.append_interview_note(
        person.person_id, content, actor_line_user_id, occurred_on, [t.value for t in sensitive_tags]
    )
    history_service.record_change(
        db=db,
        actor_line_user_id=actor_line_user_id,
        target_person_id=str(person.person_id),
        operation_type="interview_note",
        field_changes={"interview_notes": {"before": len(person.interview_notes), "after": len(updated.interview_notes)}},
        before_snapshot=None,
        after_snapshot={"note_count": len(updated.interview_notes)},
        raw_input_text=raw_input_text,
        confirmed=True,  # 面談記録の追記はポリシー上、確認なしで保存する
        result="success",
    )
    return updated


def delete_note_by_date(
    repo: PersonRepository, db, actor_line_user_id: str, person: Person, occurred_on: date, raw_input_text: str
) -> tuple[Person | None, str]:
    matches = [n for n in person.interview_notes if n.occurred_on == occurred_on and not n.deleted]
    if not matches:
        return None, f"{occurred_on.isoformat()}の面談記録が見つかりませんでした。"
    if len(matches) > 1:
        return None, f"{occurred_on.isoformat()}の面談記録が複数見つかりました。日時での特定が必要です（現状は日付単位のみ対応）。"
    note = matches[0]
    updated = repo.mark_interview_note_deleted(person.person_id, note.note_id)
    history_service.record_change(
        db=db,
        actor_line_user_id=actor_line_user_id,
        target_person_id=str(person.person_id),
        operation_type="delete_interview_note",
        field_changes={"note_id": {"before": str(note.note_id), "after": "deleted"}},
        before_snapshot=None,
        after_snapshot=None,
        raw_input_text=raw_input_text,
        confirmed=True,
        result="success",
    )
    return updated, f"{occurred_on.isoformat()}の面談記録を削除しました。"
