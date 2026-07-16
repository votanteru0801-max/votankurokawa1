"""更新: 面談記録追記・基本情報変更確認・変更前後保存・取り消し・論理削除・冪等性。"""
from __future__ import annotations

import uuid

from app.ai.tool_executor import ToolContext, execute_tool


def _existing_person(repo):
    return repo.list_all()[0]  # 「サンプル 太郎」


def test_interview_note_saved_without_confirmation(orchestrator, repo, allowed_user_id):
    person = _existing_person(repo)
    before_count = len(person.interview_notes)
    msgs = orchestrator.handle_message(
        allowed_user_id, f"今日の{person.name}との面談内容を記録して：意欲的に業務に取り組んでいた。", "ev1"
    )
    assert "記録しました" in msgs[0]
    updated = repo.get_person(person.person_id)
    assert len(updated.interview_notes) == before_count + 1
    assert "意欲的" in updated.interview_notes[-1].content


def test_basic_info_change_requires_confirmation(orchestrator, repo, allowed_user_id):
    person = _existing_person(repo)
    msgs = orchestrator.handle_message(allowed_user_id, f"{person.name}の役職をマネージャーに変更して", "ev1")
    assert "変更します" in msgs[0]
    # 確認前は反映されていない
    assert repo.get_person(person.person_id).position != "マネージャー"

    msgs = orchestrator.handle_message(allowed_user_id, "変更する", "ev2")
    assert "更新しました" in msgs[0]
    assert repo.get_person(person.person_id).position == "マネージャー"


def test_basic_info_change_records_before_after(orchestrator, repo, allowed_user_id, db_session):
    from sqlalchemy import select

    from app.db.models import ChangeHistory

    person = _existing_person(repo)
    original_position = person.position
    orchestrator.handle_message(allowed_user_id, f"{person.name}の役職を統括マネージャーに変更して", "ev1")
    orchestrator.handle_message(allowed_user_id, "変更する", "ev2")

    change = db_session.execute(
        select(ChangeHistory).where(ChangeHistory.operation_type == "update_basic_info")
    ).scalars().first()
    assert change is not None
    assert change.field_changes["position"]["before"] == original_position
    assert change.field_changes["position"]["after"] == "統括マネージャー"


def test_undo_last_change_reverts_update(orchestrator, repo, allowed_user_id):
    person = _existing_person(repo)
    original_position = person.position
    orchestrator.handle_message(allowed_user_id, f"{person.name}の役職を臨時管理職に変更して", "ev1")
    orchestrator.handle_message(allowed_user_id, "変更する", "ev2")
    assert repo.get_person(person.person_id).position == "臨時管理職"

    msgs = orchestrator.handle_message(allowed_user_id, "直前の変更を取り消して", "ev3")
    assert "取り消しました" in msgs[0]
    assert repo.get_person(person.person_id).position == original_position


def test_undo_with_no_history_returns_safe_message(orchestrator, allowed_user_id):
    msgs = orchestrator.handle_message(allowed_user_id, "直前の変更を取り消して", "ev1")
    assert "取り消せる操作がありません" in msgs[0]


def test_soft_delete_is_logical_not_physical(db_session, repo, allowed_user_id):
    from app.schemas.person import RetentionStatus

    person = _existing_person(repo)
    ctx = ToolContext(allowed_user_id, db_session, repo)
    result = execute_tool(
        "soft_delete_record",
        {"person_id": str(person.person_id), "confirmed": True, "raw_input_text": "削除テスト"},
        ctx,
    )
    assert result["status"] == "deleted"
    updated = repo.get_person(person.person_id)
    assert updated.retention.deletion_status == RetentionStatus.SOFT_DELETED
    # 論理削除のため、データ自体は引き続き取得できる（物理削除ではない）
    assert updated is not None


def test_webhook_event_idempotency(db_session):
    from app.db.models import WebhookEvent

    event_id = f"idem-test-{uuid.uuid4()}"
    db_session.add(
        WebhookEvent(
            id=uuid.uuid4(), line_event_id=event_id, line_user_id="Uxxx",
            event_type="message", raw_payload={}, status="done",
        )
    )
    db_session.commit()

    existing = db_session.query(WebhookEvent).filter_by(line_event_id=event_id).one_or_none()
    assert existing is not None
    assert existing.status == "done"
    # 同一event_idでの再挿入はユニーク制約により拒否されるべき
    import pytest
    from sqlalchemy.exc import IntegrityError

    db_session.add(
        WebhookEvent(
            id=uuid.uuid4(), line_event_id=event_id, line_user_id="Uxxx",
            event_type="message", raw_payload={}, status="processing",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
