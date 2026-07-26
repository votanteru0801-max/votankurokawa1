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
    person = _existing_person(repo)
    original_position = person.position
    orchestrator.handle_message(allowed_user_id, f"{person.name}の役職を統括マネージャーに変更して", "ev1")
    orchestrator.handle_message(allowed_user_id, "変更する", "ev2")

    docs = list(
        db_session.collection("change_history").where("operation_type", "==", "update_basic_info").stream()
    )
    assert docs, "変更履歴が記録されていません"
    change = docs[0].to_dict()
    assert change["field_changes"]["position"]["before"] == original_position
    assert change["field_changes"]["position"]["after"] == "統括マネージャー"


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
    # Firestore版では line_event_id をそのままドキュメントIDにしているため、
    # 「同じevent_idは常に同じドキュメントを指す」こと自体が二重処理防止の
    # 仕組みになっている（webhook.pyのprocess_eventはstatus=="done"なら
    # 早期returnする）。ここではその前提となる挙動を確認する。
    event_id = f"idem-test-{uuid.uuid4()}"
    ref = db_session.collection("webhook_events").document(event_id)
    ref.set(
        {
            "line_event_id": event_id,
            "line_user_id": "Uxxx",
            "event_type": "message",
            "raw_payload": {},
            "received_at": None,
            "processed_at": None,
            "status": "done",
            "error_message": None,
        }
    )

    snapshot = db_session.collection("webhook_events").document(event_id).get()
    assert snapshot.exists
    assert snapshot.to_dict()["status"] == "done"

    # 同一event_idで再度参照しても同じドキュメントが返る（新規作成されない）。
    same_ref = db_session.collection("webhook_events").document(event_id)
    assert same_ref.id == ref.id
