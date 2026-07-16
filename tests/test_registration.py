"""登録フロー: 一括入力・質問形式・必須情報不足・出生時間不明・同姓同名・
重複登録・確認後の登録・登録中止。
"""
from __future__ import annotations

from app.schemas.person import PersonCategory


def test_bulk_registration_happy_path(orchestrator, repo, allowed_user_id):
    msgs = orchestrator.handle_message(
        allowed_user_id, "採用候補者を登録。山田花子、2003年5月10日、10時30分、福岡県福岡市、女性", "ev1"
    )
    assert "登録しますか" in msgs[0]
    assert "山田花子" in msgs[0]

    msgs = orchestrator.handle_message(allowed_user_id, "登録する", "ev2")
    assert "登録しました" in msgs[0]

    people = repo.find_by_name("山田花子")
    assert len(people) == 1
    assert people[0].category == PersonCategory.CANDIDATE
    assert people[0].birth_time_unknown is False


def test_bulk_registration_missing_required_fields_triggers_qa(orchestrator, allowed_user_id):
    msgs = orchestrator.handle_message(allowed_user_id, "社員を登録、佐藤次郎", "ev1")
    assert "不足しています" in msgs[0]
    # 生年月日等、次の質問が続けて返される
    assert any("生年月日" in m for m in msgs)


def test_qa_registration_full_flow(orchestrator, repo, allowed_user_id):
    msgs = orchestrator.handle_message(allowed_user_id, "人物を登録", "ev1")
    assert "人物区分" in msgs[0]

    msgs = orchestrator.handle_message(allowed_user_id, "社員", "ev2")
    assert "氏名" in msgs[0]

    msgs = orchestrator.handle_message(allowed_user_id, "佐藤次郎", "ev3")
    assert "生年月日" in msgs[0]

    msgs = orchestrator.handle_message(allowed_user_id, "1990年4月12日", "ev4")
    assert "出生時間" in msgs[0]

    msgs = orchestrator.handle_message(allowed_user_id, "不明", "ev5")
    assert "出生" in msgs[0]  # 出生都道府県・市区町村

    msgs = orchestrator.handle_message(allowed_user_id, "東京都渋谷区", "ev6")
    assert "性別" in msgs[0]

    msgs = orchestrator.handle_message(allowed_user_id, "男性", "ev7")
    assert "登録しますか" in msgs[0]

    msgs = orchestrator.handle_message(allowed_user_id, "登録する", "ev8")
    assert "登録しました" in msgs[0]

    people = repo.find_by_name("佐藤次郎")
    assert len(people) == 1
    assert people[0].birth_time_unknown is True


def test_birth_time_unknown_registration(orchestrator, repo, allowed_user_id):
    msgs = orchestrator.handle_message(
        allowed_user_id, "社員を登録。鈴木一郎、1985年3月3日、大阪府、男性", "ev1"
    )
    assert "出生時間: 不明" in msgs[0]
    orchestrator.handle_message(allowed_user_id, "登録する", "ev2")
    person = repo.find_by_name("鈴木一郎")[0]
    assert person.birth_time_unknown is True
    assert person.birth_time is None


def test_duplicate_name_registration_asks_disambiguation(orchestrator, repo, allowed_user_id):
    # サンプル人物リポジトリには既に「サンプル 太郎」が存在する
    msgs = orchestrator.handle_message(
        allowed_user_id, "社員を登録。サンプル 太郎、1999年9月9日、北海道、男性", "ev1"
    )
    assert "同姓同名" in msgs[0]

    msgs = orchestrator.handle_message(allowed_user_id, "新規登録", "ev2")
    assert "登録しますか" in msgs[0]

    msgs = orchestrator.handle_message(allowed_user_id, "登録する", "ev3")
    assert "登録しました" in msgs[0]

    assert len(repo.find_by_name("サンプル 太郎")) == 2


def test_registration_cancel(orchestrator, repo, allowed_user_id):
    msgs = orchestrator.handle_message(
        allowed_user_id, "講師を登録。中止太郎、1980年1月1日、東京都、男性", "ev1"
    )
    assert "登録しますか" in msgs[0]
    msgs = orchestrator.handle_message(allowed_user_id, "中止する", "ev2")
    assert "中止しました" in msgs[0]
    assert repo.find_by_name("中止太郎") == []


def test_registration_correction_restarts_qa(orchestrator, allowed_user_id):
    orchestrator.handle_message(allowed_user_id, "パートナーを登録。修正花子、1975年5月5日、京都府、女性", "ev1")
    msgs = orchestrator.handle_message(allowed_user_id, "修正する", "ev2")
    assert "人物区分" in msgs[-1]
