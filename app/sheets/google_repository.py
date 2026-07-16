"""Google Sheets APIを用いた本番用リポジトリ実装。

未検証: 実際のスプレッドシート構成（docs/current-sheet-schema.md）が確認でき次第、
schema_mapping.py と併せて調整すること。現時点では認証情報がないため実行テストは
行っていない（golden_tests/testsではMockPersonRepositoryのみ使用）。
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from app.config import get_settings
from app.schemas.person import Person, PersonSearchQuery
from app.sheets.schema_mapping import COLUMN_TO_FIELD, PERSON_SHEET_NAME


class GoogleSheetsPersonRepository:
    """PersonRepository Protocolの本番実装。

    google-api-python-client を用いて Sheets API v4 を呼び出す。
    レート制限（1分あたり読み取り300回等）を考慮し、人物一覧はアプリ側で
    短時間キャッシュ（PersonIndexCache）することを推奨する。
    """

    def __init__(self, spreadsheet_id: str | None = None):
        settings = get_settings()
        self.spreadsheet_id = spreadsheet_id or settings.hr_spreadsheet_id
        self._service = None  # 遅延初期化（認証情報が無い環境でのimportエラーを避ける）

    def _get_service(self):
        if self._service is None:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            settings = get_settings()
            credentials = service_account.Credentials.from_service_account_file(
                settings.google_application_credentials,
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            self._service = build("sheets", "v4", credentials=credentials)
        return self._service

    def _read_all_rows(self) -> tuple[list[str], list[list[str]]]:
        service = self._get_service()
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=f"{PERSON_SHEET_NAME}!A1:ZZ")
            .execute()
        )
        values = result.get("values", [])
        if not values:
            return [], []
        header, *rows = values
        return header, rows

    def _row_to_person(self, header: list[str], row: list[str]) -> Person | None:
        row_dict = dict(zip(header, row + [""] * (len(header) - len(row))))
        mapped: dict = {}
        for col, field in COLUMN_TO_FIELD.items():
            if col in row_dict:
                mapped[field] = row_dict[col]
        if not mapped.get("person_id") or not mapped.get("name"):
            return None
        # NOTE: 実データ確認後、型変換（日付/真偽値/ネスト構造）をここで厳密に実装する。
        # 現状は骨格のみ（未検証）。
        raise NotImplementedError(
            "GoogleSheetsPersonRepositoryの行->Personマッピングは実シート構造確認後に実装します。"
            " docs/current-sheet-schema.md と docs/INPUT_REQUIRED.md を参照してください。"
        )

    def search_people(self, query: PersonSearchQuery) -> list[Person]:
        raise NotImplementedError("Sheets実データ確認後に実装（docs/INPUT_REQUIRED.md参照）")

    def get_person(self, person_id: UUID) -> Person | None:
        raise NotImplementedError("Sheets実データ確認後に実装（docs/INPUT_REQUIRED.md参照）")

    def find_by_name(self, name: str) -> list[Person]:
        raise NotImplementedError("Sheets実データ確認後に実装（docs/INPUT_REQUIRED.md参照）")

    def create_person(self, person: Person) -> Person:
        raise NotImplementedError("Sheets実データ確認後に実装（docs/INPUT_REQUIRED.md参照）")

    def update_person_fields(self, person_id: UUID, changes: dict) -> Person:
        raise NotImplementedError("Sheets実データ確認後に実装（docs/INPUT_REQUIRED.md参照）")

    def append_interview_note(self, person_id: UUID, note_content: str, author_line_user_id: str,
                               occurred_on: date, sensitive_tags: list[str]) -> Person:
        raise NotImplementedError("Sheets実データ確認後に実装（docs/INPUT_REQUIRED.md参照）")

    def soft_delete(self, person_id: UUID) -> Person:
        raise NotImplementedError("Sheets実データ確認後に実装（docs/INPUT_REQUIRED.md参照）")

    def list_all(self) -> list[Person]:
        raise NotImplementedError("Sheets実データ確認後に実装（docs/INPUT_REQUIRED.md参照）")


def get_person_repository():
    """設定に応じてモック/本番実装を返すファクトリ。"""
    settings = get_settings()
    if settings.google_sheets_mode.value == "live":
        return GoogleSheetsPersonRepository()
    from app.sheets.mock_repository import MockPersonRepository

    return MockPersonRepository()
