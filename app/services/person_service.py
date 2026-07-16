"""人物の登録・更新・削除に関するアプリケーション層のロジック。
LLMは一切書き込みを直接実行しない。ここが唯一の書き込み経路であり、
権限・入力検証・確認・監査ログをすべてここで担保する。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from app.line.nl_registration_parser import ParsedRegistration
from app.schemas.person import Gender, Person, PersonCategory, RetentionInfo
from app.services import history_service
from app.sheets.interface import PersonRepository

CATEGORY_LABELS = {
    PersonCategory.EMPLOYEE: "社員",
    PersonCategory.CANDIDATE: "採用候補者",
    PersonCategory.EXTERNAL_CONSULTANT: "外部コンサルタント",
    PersonCategory.BUSINESS_PARTNER: "取引先",
    PersonCategory.INSTRUCTOR: "講師",
    PersonCategory.PARTNER: "パートナー",
    PersonCategory.OTHER: "その他",
}

GENDER_LABELS = {Gender.MALE: "男性", Gender.FEMALE: "女性", Gender.OTHER: "その他", Gender.UNKNOWN: "未登録"}

RETENTION_POLICY_BY_CATEGORY = {
    PersonCategory.CANDIDATE: "candidate_6m_after_selection",
    PersonCategory.EMPLOYEE: "employee_1y_after_resignation",
}

REGISTRATION_QUESTION_ORDER = ["category", "name", "birth_date", "birth_time", "prefecture", "gender"]

QUESTION_TEXT = {
    "category": "人物区分を教えてください（社員/採用候補者/外部コンサルタント/取引先/講師/パートナー/その他）。",
    "name": "氏名を教えてください。",
    "birth_date": "生年月日を教えてください（例: 1990年4月12日）。",
    "birth_time": "出生時間を教えてください（不明な場合は「不明」とお答えください）。",
    "prefecture": "出生都道府県・市区町村を教えてください。",
    "gender": "性別を教えてください（男性/女性/その他）。",
}


@dataclass
class RegistrationOutcome:
    status: str  # ask_field | confirm_required | duplicate_check_required | registered | cancelled
    message: str
    parsed: ParsedRegistration | None = None
    next_field: str | None = None
    candidates: list[Person] = field(default_factory=list)
    person: Person | None = None


def next_missing_question_field(parsed: ParsedRegistration, asked: set[str]) -> str | None:
    for f in REGISTRATION_QUESTION_ORDER:
        if f in asked:
            continue
        if f == "category" and parsed.category is None:
            return f
        if f == "name" and not parsed.name:
            return f
        if f == "birth_date" and parsed.birth_date is None:
            return f
        if f == "birth_time" and parsed.birth_time is None and parsed.birth_time_unknown is True and "birth_time" not in asked:
            return f
        if f == "prefecture" and not parsed.prefecture:
            return f
        if f == "gender" and parsed.gender == Gender.UNKNOWN:
            return f
    return None


def apply_answer(parsed: ParsedRegistration, field_name: str, answer_text: str) -> ParsedRegistration:
    from app.line.nl_registration_parser import CATEGORY_KEYWORDS, PREFECTURES

    answer_text = answer_text.strip()
    if field_name == "category":
        for kw, cat in CATEGORY_KEYWORDS.items():
            if kw in answer_text:
                parsed.category = cat
                break
    elif field_name == "name":
        parsed.name = answer_text
    elif field_name == "birth_date":
        import re

        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", answer_text)
        if m:
            y, mo, d = map(int, m.groups())
            try:
                parsed.birth_date = date(y, mo, d)
            except ValueError:
                pass
        else:
            m2 = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", answer_text)
            if m2:
                y, mo, d = map(int, m2.groups())
                try:
                    parsed.birth_date = date(y, mo, d)
                except ValueError:
                    pass
    elif field_name == "birth_time":
        import re

        if "不明" in answer_text:
            parsed.birth_time = None
            parsed.birth_time_unknown = True
        else:
            m = re.search(r"(\d{1,2})時(\d{1,2})?分?", answer_text) or re.search(r"(\d{1,2}):(\d{2})", answer_text)
            if m:
                from datetime import time

                h = int(m.group(1))
                mi = int(m.group(2)) if m.group(2) else 0
                if 0 <= h < 24 and 0 <= mi < 60:
                    parsed.birth_time = time(h, mi)
                    parsed.birth_time_unknown = False
    elif field_name == "prefecture":
        matched = next((p for p in PREFECTURES if answer_text.startswith(p)), None)
        if matched:
            parsed.prefecture = matched
            city = answer_text[len(matched):].strip()
            if city:
                parsed.city = city
        else:
            parsed.prefecture = answer_text
    elif field_name == "gender":
        if "男" in answer_text:
            parsed.gender = Gender.MALE
        elif "女" in answer_text:
            parsed.gender = Gender.FEMALE
        else:
            parsed.gender = Gender.OTHER
    return parsed


def build_confirmation_message(parsed: ParsedRegistration) -> str:
    category_label = CATEGORY_LABELS.get(parsed.category, "未設定") if parsed.category else "未設定"
    gender_label = GENDER_LABELS.get(parsed.gender, "未登録")
    birth_time_label = parsed.birth_time.strftime("%H:%M") if parsed.birth_time else "不明"
    place = f"{parsed.prefecture or ''}{parsed.city or ''}" or "未登録"
    return (
        "以下の内容で登録しますか？\n"
        f"名前: {parsed.name}\n"
        f"区分: {category_label}\n"
        f"生年月日: {parsed.birth_date.isoformat() if parsed.birth_date else '未登録'}\n"
        f"出生時間: {birth_time_label}\n"
        f"出生地: {place}\n"
        f"性別: {gender_label}\n\n"
        "「登録する」「修正する」「中止する」でお答えください。"
    )


def check_duplicates(repo: PersonRepository, name: str) -> list[Person]:
    return repo.find_by_name(name)


def register_confirmed(
    repo: PersonRepository,
    db,
    actor_line_user_id: str,
    parsed: ParsedRegistration,
    raw_input_text: str,
) -> Person:
    retention_policy = RETENTION_POLICY_BY_CATEGORY.get(parsed.category, "manual")
    person = Person(
        person_id=uuid.uuid4(),
        name=parsed.name or "",
        category=parsed.category,
        gender=parsed.gender,
        birth_date=parsed.birth_date,
        birth_time=parsed.birth_time,
        birth_time_unknown=parsed.birth_time_unknown,
        birth_prefecture=parsed.prefecture or "",
        birth_city=parsed.city or "",
        status="選考中" if parsed.category == PersonCategory.CANDIDATE else "在籍",
        retention=RetentionInfo(retention_policy=retention_policy, retention_start_date=date.today()),
    )
    created = repo.create_person(person)
    history_service.record_change(
        db=db,
        actor_line_user_id=actor_line_user_id,
        target_person_id=str(created.person_id),
        operation_type="register",
        field_changes={},
        before_snapshot=None,
        after_snapshot=created.model_dump(mode="json"),
        raw_input_text=raw_input_text,
        confirmed=True,
        result="success",
    )
    return created


def prepare_basic_info_update(
    repo: PersonRepository, person: Person, field_name: str, new_value: str
) -> dict:
    """変更内容のプレビューを返す（実反映はconfirm側で行う）。"""
    before_value = getattr(person, field_name)
    before_str = before_value.isoformat() if hasattr(before_value, "isoformat") else str(before_value)
    return {
        "person_id": str(person.person_id),
        "field": field_name,
        "before": before_str,
        "after": new_value,
    }


def confirm_basic_info_update(
    repo: PersonRepository, db, actor_line_user_id: str, person: Person, field_name: str,
    before_value: str, new_value: str, raw_input_text: str,
) -> Person:
    updated = repo.update_person_fields(person.person_id, {field_name: new_value})
    history_service.record_change(
        db=db,
        actor_line_user_id=actor_line_user_id,
        target_person_id=str(person.person_id),
        operation_type="update_basic_info",
        field_changes={field_name: {"before": before_value, "after": new_value}},
        before_snapshot=person.model_dump(mode="json"),
        after_snapshot=updated.model_dump(mode="json"),
        raw_input_text=raw_input_text,
        confirmed=True,
        result="success",
    )
    return updated


def soft_delete_confirmed(repo: PersonRepository, db, actor_line_user_id: str, person: Person, raw_input_text: str) -> Person:
    updated = repo.soft_delete(person.person_id)
    history_service.record_change(
        db=db,
        actor_line_user_id=actor_line_user_id,
        target_person_id=str(person.person_id),
        operation_type="soft_delete",
        field_changes={"deletion_status": {"before": "active", "after": "soft_deleted"}},
        before_snapshot=person.model_dump(mode="json"),
        after_snapshot=updated.model_dump(mode="json"),
        raw_input_text=raw_input_text,
        confirmed=True,
        result="success",
    )
    return updated


def resolve_person_by_name(repo: PersonRepository, name: str) -> tuple[Person | None, list[Person]]:
    matches = repo.find_by_name(name)
    if len(matches) == 1:
        return matches[0], []
    if len(matches) == 0:
        return None, []
    return None, matches


def build_disambiguation_message(candidates: list[Person]) -> str:
    lines = ["同姓同名の可能性がある人物が複数見つかりました。対象を教えてください。"]
    for i, p in enumerate(candidates, start=1):
        cat = CATEGORY_LABELS.get(p.category, p.category)
        lines.append(f"{i}. {p.name}（{cat} / {p.department or '所属未登録'} / {p.birth_date or '生年月日未登録'}）")
    return "\n".join(lines)
