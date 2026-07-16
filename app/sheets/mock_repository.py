"""ローカル開発・テスト用のインメモリ人事情報リポジトリ。
Google Sheets APIの認証情報がなくても全フローを試せるようにする。
ここに含まれる人物データはすべて架空のサンプルであり、実在の人物とは無関係。
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from uuid import UUID

from app.schemas.person import (
    Evaluation,
    Gender,
    InterviewNote,
    Person,
    PersonCategory,
    PersonSearchQuery,
    RetentionInfo,
    RetentionStatus,
)


def _sample_people() -> list[Person]:
    return [
        Person(
            person_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            name="サンプル 太郎",
            kana="サンプル タロウ",
            category=PersonCategory.EMPLOYEE,
            gender=Gender.MALE,
            birth_date=date(1990, 4, 12),
            birth_time=time(8, 30),
            birth_time_unknown=False,
            birth_prefecture="東京都",
            birth_city="世田谷区",
            department="営業本部 第一営業部",
            position="マネージャー",
            hire_date=date(2015, 4, 1),
            status="在籍",
            mbti="ENTJ",
            desired_career="将来的に部門統括を目指したい",
            evaluations=[Evaluation(period="2025年下期", summary="目標達成率120%。リーダーシップ良好。")],
            interview_notes=[
                InterviewNote(
                    occurred_on=date(2026, 6, 1),
                    author_line_user_id="mock-user",
                    content="次のプロジェクトでリーダー経験を積みたいと希望。",
                )
            ],
            retention=RetentionInfo(retention_policy="employee_1y_after_resignation"),
        ),
        Person(
            person_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            name="サンプル 花子",
            kana="サンプル ハナコ",
            category=PersonCategory.CANDIDATE,
            gender=Gender.FEMALE,
            birth_date=date(2003, 5, 10),
            birth_time=time(10, 30),
            birth_time_unknown=False,
            birth_prefecture="福岡県",
            birth_city="福岡市",
            status="選考中",
            retention=RetentionInfo(retention_policy="candidate_6m_after_selection"),
        ),
        Person(
            person_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            name="サンプル 次郎",
            kana="サンプル ジロウ",
            category=PersonCategory.EMPLOYEE,
            gender=Gender.MALE,
            birth_date=date(1988, 11, 2),
            birth_time_unknown=True,
            birth_prefecture="大阪府",
            department="Senne事業部",
            position="スタッフ",
            hire_date=date(2018, 7, 1),
            status="在籍",
            retention=RetentionInfo(retention_policy="employee_1y_after_resignation"),
        ),
    ]


class MockPersonRepository:
    """Protocol PersonRepository を満たすインメモリ実装。"""

    def __init__(self) -> None:
        self._people: dict[UUID, Person] = {p.person_id: p for p in _sample_people()}

    def search_people(self, query: PersonSearchQuery) -> list[Person]:
        results = list(self._people.values())
        if query.name_query:
            q = query.name_query.replace(" ", "").replace("　", "")
            results = [
                p for p in results
                if q in p.name.replace(" ", "").replace("　", "")
                or q in p.kana.replace(" ", "").replace("　", "")
            ]
        if query.category:
            results = [p for p in results if p.category == query.category]
        if query.department:
            results = [p for p in results if query.department in p.department]
        return results[: query.limit]

    def get_person(self, person_id: UUID) -> Person | None:
        return self._people.get(person_id)

    def find_by_name(self, name: str) -> list[Person]:
        norm = name.replace(" ", "").replace("　", "")
        return [p for p in self._people.values() if p.name.replace(" ", "").replace("　", "") == norm]

    def create_person(self, person: Person) -> Person:
        self._people[person.person_id] = person
        return person

    def update_person_fields(self, person_id: UUID, changes: dict) -> Person:
        person = self._people[person_id]
        updated = person.model_copy(update={**changes, "updated_at": datetime.utcnow()})
        self._people[person_id] = updated
        return updated

    def append_interview_note(
        self, person_id: UUID, note_content: str, author_line_user_id: str, occurred_on, sensitive_tags: list[str]
    ) -> Person:
        person = self._people[person_id]
        note = InterviewNote(
            occurred_on=occurred_on,
            author_line_user_id=author_line_user_id,
            content=note_content,
            sensitive_tags=sensitive_tags,
        )
        updated = person.model_copy(
            update={"interview_notes": [*person.interview_notes, note], "updated_at": datetime.utcnow()}
        )
        self._people[person_id] = updated
        return updated

    def soft_delete(self, person_id: UUID) -> Person:
        person = self._people[person_id]
        retention = person.retention.model_copy(update={"deletion_status": RetentionStatus.SOFT_DELETED})
        updated = person.model_copy(update={"retention": retention, "updated_at": datetime.utcnow()})
        self._people[person_id] = updated
        return updated

    def remove_last_interview_note(self, person_id: UUID) -> Person:
        person = self._people[person_id]
        if not person.interview_notes:
            return person
        updated = person.model_copy(
            update={"interview_notes": person.interview_notes[:-1], "updated_at": datetime.utcnow()}
        )
        self._people[person_id] = updated
        return updated

    def restore(self, person_id: UUID) -> Person:
        person = self._people[person_id]
        retention = person.retention.model_copy(update={"deletion_status": RetentionStatus.ACTIVE})
        updated = person.model_copy(update={"retention": retention, "updated_at": datetime.utcnow()})
        self._people[person_id] = updated
        return updated

    def mark_interview_note_deleted(self, person_id: UUID, note_id) -> Person:
        person = self._people[person_id]
        new_notes = [
            n.model_copy(update={"deleted": True}) if n.note_id == note_id else n
            for n in person.interview_notes
        ]
        updated = person.model_copy(update={"interview_notes": new_notes, "updated_at": datetime.utcnow()})
        self._people[person_id] = updated
        return updated

    def list_all(self) -> list[Person]:
        return list(self._people.values())
