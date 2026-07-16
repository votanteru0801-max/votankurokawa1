"""人事情報リポジトリの抽象インターフェース。
本番はGoogleスプレッドシート実装、ローカル/テストはモック実装に差し替える。
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.schemas.person import Person, PersonSearchQuery


class PersonRepository(Protocol):
    def search_people(self, query: PersonSearchQuery) -> list[Person]:
        """氏名・フリガナ・部署等による検索（表記揺れにある程度耐性を持たせる）。"""
        ...

    def get_person(self, person_id: UUID) -> Person | None:
        ...

    def find_by_name(self, name: str) -> list[Person]:
        """同姓同名判定に使う。完全一致・部分一致の候補を返す。"""
        ...

    def create_person(self, person: Person) -> Person:
        ...

    def update_person_fields(self, person_id: UUID, changes: dict) -> Person:
        """既存列の削除・改名は行わず、値のみ更新する。"""
        ...

    def append_interview_note(self, person_id: UUID, note_content: str, author_line_user_id: str,
                               occurred_on, sensitive_tags: list[str]) -> Person:
        ...

    def soft_delete(self, person_id: UUID) -> Person:
        ...

    def list_all(self) -> list[Person]:
        ...

    def remove_last_interview_note(self, person_id: UUID) -> Person:
        """直前の面談記録を取り消す（undo専用）。"""
        ...

    def restore(self, person_id: UUID) -> Person:
        """論理削除を取り消し、在籍/選考中等の状態に戻す（undo専用）。"""
        ...

    def mark_interview_note_deleted(self, person_id: UUID, note_id) -> Person:
        """特定の面談記録を論理削除する。"""
        ...
