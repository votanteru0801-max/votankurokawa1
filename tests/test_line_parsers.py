"""LINE自然文パーサーの単体テスト（DB不要）。"""
from __future__ import annotations

from datetime import date, time

from app.line.nl_registration_parser import parse_bulk_registration_text
from app.line.nl_update_parser import parse_update_command
from app.schemas.person import Gender, PersonCategory


def test_parse_bulk_registration_full_example():
    parsed = parse_bulk_registration_text("採用候補者を登録。山田花子、2003年5月10日、10時30分、福岡県福岡市、女性")
    assert parsed.category == PersonCategory.CANDIDATE
    assert parsed.name == "山田花子"
    assert parsed.birth_date == date(2003, 5, 10)
    assert parsed.birth_time == time(10, 30)
    assert parsed.birth_time_unknown is False
    assert parsed.prefecture == "福岡県"
    assert parsed.city == "福岡市"
    assert parsed.gender == Gender.FEMALE
    assert parsed.missing_required_fields() == []


def test_parse_bulk_registration_missing_fields():
    parsed = parse_bulk_registration_text("社員を登録、田中太郎")
    missing = parsed.missing_required_fields()
    assert "生年月日" in missing
    assert "性別" in missing


def test_parse_undo_command():
    cmd = parse_update_command("直前の変更を取り消して")
    assert cmd.kind == "undo"


def test_parse_career_append_command():
    cmd = parse_update_command("木村優花の希望キャリアに、執行役員を目指したいと追加して")
    assert cmd.kind == "career_append"
    assert cmd.person_name == "木村優花"
    assert "執行役員" in cmd.value


def test_parse_basic_field_update_command():
    cmd = parse_update_command("木村優花の役職をマネージャーに変更して")
    assert cmd.kind == "basic_field_update"
    assert cmd.field_name == "position"
    assert cmd.value == "マネージャー"


def test_parse_interview_note_command_with_inline_content():
    cmd = parse_update_command("今日の木村優花との面談内容を記録して：目標達成に前向きだった")
    assert cmd.kind == "interview_note"
    assert cmd.person_name == "木村優花"
    assert "目標達成" in cmd.content


def test_parse_delete_interview_note_command():
    cmd = parse_update_command("6月1日の面談記録を削除して")
    assert cmd.kind == "delete_interview_note"
    assert cmd.extra == {"month": 6, "day": 1}


def test_parse_unrecognized_command():
    cmd = parse_update_command("こんにちは、元気ですか")
    assert cmd.kind == "unrecognized"
