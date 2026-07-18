"""Google Sheets APIを用いた本番用リポジトリ実装。

実シート構成の調査結果（2026-07-17確認）:
実際のスプレッドシート（タブ名「生年月日」）は、1行1人の単一テーブルではなく、
店舗・チームごとに「名前」を先頭列とする小さな表がシート内に複数（横にも縦にも）
並んでいる手作業運用のレイアウトだった。列の並びはブロックごとに微妙に異なり
（例: 一部のブロックだけ「名前」と「生年月日」の間に非表示の「性別」列が
挿入されている）、固定の列位置では正しく読み取れないことが判明した。
person_id・人物区分・部署コード・面談記録・評価などの列は存在しない。

このため、当面は以下の方針で実装する（ユーザー確認済み・2026-07-17）:
- 既存の「生年月日」タブは一切変更しない（列追加・並び替えをしない）。
- 「名前」というセルを見出し行の起点として検出し、そこから右方向に隣接する
  セルを見出し名（性別/生年月日/時間/場所/MBTI等）として読み取り、ブロックごとに
  列の並びを個別に判定する（固定オフセットに依存しない）。
- 各ブロックのタイトル（ブロック開始行の直上にある空でないセル）を
  department（所属店舗）として扱う。
- 人物区分（category）は全員 employee とみなす（シート上に区別する情報がないため）。
- person_id はシート上に存在しないため、department・name・生年月日文字列から
  決定論的に生成する（uuid5）。同じ人物なら常に同じIDになるが、店舗異動や
  表記揺れで名前が変わると別人扱いになる点に注意。
- create_person / update_person_fields / append_interview_note / soft_delete など
  書き込み系は非対応。SheetsWriteNotSupportedError を送出し、呼び出し側
  （app/line/webhook.py）でユーザーに分かりやすいメッセージを返す。
"""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, time
from uuid import UUID

from app.config import get_settings
from app.schemas.person import Gender, Person, PersonCategory, PersonSearchQuery, RetentionInfo

BIRTHDAY_SHEET_NAME = "生年月日"

# 見出しセルの文字列 -> 内部フィールド名。ここに無い見出し列は無視する。
HEADER_ALIASES: dict[str, str] = {
    "名前": "name",
    "氏名": "name",
    "性別": "gender",
    "生年月日": "birth_date",
    "時間": "time",
    "出生時間": "time",
    "場所": "place",
    "出生地": "place",
    "MBTI": "mbti",
}
# ヘッダー行を右方向にスキャンする際、この個数まで空セルが続いたら
# ブロックの見出しが終わったとみなす（列の間にちょっとした空白列があっても
# 誤って別ブロックと混ざらないようにするため、1で十分＝空セル1つで終了）。
_HEADER_SCAN_MAX_COLS = 8

# person_idを決定論的に生成するための固定名前空間（変更しないこと。変更すると
# 既存の全人物IDが変わってしまう）。
_PERSON_ID_NAMESPACE = uuid.UUID("2f6a9e2a-2f0e-4c7b-9d1a-6f7c1b4e9a11")


def _parse_gender(raw: str) -> Gender:
    raw = (raw or "").strip()
    if raw in ("男", "男性", "M", "m"):
        return Gender.MALE
    if raw in ("女", "女性", "F", "f"):
        return Gender.FEMALE
    if not raw:
        return Gender.UNKNOWN
    return Gender.OTHER


class SheetsWriteNotSupportedError(Exception):
    """現在のシート構成では書き込み系操作に対応していないことを表す。"""


def _norm_name(s: str) -> str:
    """氏名比較用の正規化。全角・半角スペースの有無による表記揺れ
    （例:「濱澤ひかり」/「濱澤 ひかり」）を吸収する。"""
    return (s or "").replace("　", "").replace(" ", "").strip()


def _make_person_id(department: str, name: str, birth_date_raw: str) -> UUID:
    key = f"{department}|{name}|{birth_date_raw}"
    return uuid.uuid5(_PERSON_ID_NAMESPACE, key)


def _parse_birth_date(raw: str) -> date | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    # 「1998.04,07」のようにカンマとピリオドが混在する入力ミスを吸収する。
    normalized = raw.replace(",", ".").replace("/", ".").replace("年", ".").replace("月", ".").replace("日", "")
    m = re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", normalized)
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _parse_birth_time(raw: str) -> tuple[time | None, bool]:
    """(time, birth_time_unknown) を返す。「頃」「多分」等の曖昧表現は時刻自体は採用しつつ
    不明フラグは立てない（人間が判断済みの推定値のため）。ただし「不明」は完全に不明扱い。
    """
    raw = (raw or "").strip()
    if not raw or "不明" in raw:
        return None, True
    cleaned = raw.replace("頃", "").replace("多分", "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", cleaned)
    if not m:
        return None, True
    h, mi = int(m.group(1)), int(m.group(2))
    if 0 <= h < 24 and 0 <= mi < 60:
        return time(h, mi), False
    return None, True


class GoogleSheetsPersonRepository:
    """PersonRepository Protocolの実装（読み取り専用・「生年月日」タブ限定）。

    書き込み系メソッドは SheetsWriteNotSupportedError を送出する。
    人物一覧は毎回シート全体を取得して解析する（キャッシュなし）。将来的に
    呼び出し頻度が増える場合は短時間キャッシュの追加を検討すること。
    """

    def __init__(self, spreadsheet_id: str | None = None):
        settings = get_settings()
        self.spreadsheet_id = spreadsheet_id or settings.hr_spreadsheet_id
        self._service = None

    def _get_service(self):
        if self._service is None:
            import json

            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            settings = get_settings()
            scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
            if settings.google_service_account_json:
                # Secret Files機能を使わず、環境変数にJSONの中身を直接入れている場合。
                info = json.loads(settings.google_service_account_json)
                credentials = service_account.Credentials.from_service_account_info(info, scopes=scopes)
            else:
                credentials = service_account.Credentials.from_service_account_file(
                    settings.google_application_credentials, scopes=scopes,
                )
            self._service = build("sheets", "v4", credentials=credentials)
        return self._service

    def _fetch_grid(self) -> list[list[str]]:
        service = self._get_service()
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=f"{BIRTHDAY_SHEET_NAME}!A1:BZ500")
            .execute()
        )
        grid = result.get("values", [])

        # 調査用: スプレッドシート内の全タブ名を確認する（同名タブが複数あり、
        # 意図しない方を読んでいないか確認するため）。
        try:
            meta = self._get_service().spreadsheets().get(
                spreadsheetId=self.spreadsheet_id, fields="sheets.properties(sheetId,title,index,gridProperties)"
            ).execute()
            for sh in meta.get("sheets", []):
                props = sh.get("properties", {})
                print(f"[SHEETS_DEBUG] tab: title={props.get('title')!r} sheetId={props.get('sheetId')} index={props.get('index')} rows={props.get('gridProperties', {}).get('rowCount')} cols={props.get('gridProperties', {}).get('columnCount')}")
        except Exception as e:
            print(f"[SHEETS_DEBUG] tab list fetch failed: {type(e).__name__}: {e}")

        # 調査用: B4セル（濱澤ひかりの性別のはず）の生データを、可能な限り
        # 詳しい情報付きで単独取得する。
        try:
            detail = (
                self._get_service()
                .spreadsheets()
                .get(
                    spreadsheetId=self.spreadsheet_id,
                    ranges=[f"{BIRTHDAY_SHEET_NAME}!B4"],
                    includeGridData=True,
                )
                .execute()
            )
            cell = detail["sheets"][0]["data"][0]["rowData"][0]["values"][0]
            print(f"[SHEETS_DEBUG] B4 full cell data = {cell}")
        except Exception as e:
            print(f"[SHEETS_DEBUG] B4 detail fetch failed: {type(e).__name__}: {e}")

        return grid

    def _department_label(self, grid: list[list[str]], row: int, col: int) -> str:
        # ヘッダー行(row)の直上から数行、同じ列を上向きに探索し、最初に見つかった
        # 空でないセルをブロックタイトル（店舗名）とみなす。別のヘッダー行に
        # ぶつかったら探索を打ち切る。
        for r in range(row - 1, max(row - 4, -1), -1):
            if r < 0 or r >= len(grid):
                continue
            line = grid[r]
            cell = line[col].strip() if col < len(line) else ""
            if cell in HEADER_ALIASES:
                break
            if cell:
                return cell
        return "不明"

    def _read_header_map(self, line: list[str], name_col: int) -> dict[str, int]:
        """name_col（「名前」セル）を起点に右方向へスキャンし、
        {フィールド名: 列インデックス} の対応表を作る。未知の見出しは無視して
        読み飛ばすが、空セルに達したらそこでスキャンを打ち切る。
        """
        field_to_col: dict[str, int] = {"name": name_col}
        c = name_col + 1
        while c < min(len(line), name_col + _HEADER_SCAN_MAX_COLS):
            cell = line[c].strip()
            if not cell:
                break
            field = HEADER_ALIASES.get(cell)
            if field and field not in field_to_col:
                field_to_col[field] = c
            c += 1
        return field_to_col

    def _parse_all(self) -> list[Person]:
        grid = self._fetch_grid()
        people: list[Person] = []
        n_rows = len(grid)
        for r in range(n_rows):
            line = grid[r]
            for c in range(len(line)):
                if line[c].strip() != "名前":
                    continue
                header_map = self._read_header_map(line, c)
                if "birth_date" not in header_map:
                    # 「名前」だけの単発セル（見出しではない）を誤検出した場合は無視する。
                    continue
                department = self._department_label(grid, r, c)

                def cell_at(row_cells: list[str], field: str) -> str:
                    col = header_map.get(field)
                    if col is None or col >= len(row_cells):
                        return ""
                    return row_cells[col].strip()

                data_row = r + 1
                while data_row < n_rows:
                    row_cells = grid[data_row]
                    name = cell_at(row_cells, "name")
                    if not name:
                        break
                    birth_raw = cell_at(row_cells, "birth_date")
                    time_raw = cell_at(row_cells, "time")
                    place_raw = cell_at(row_cells, "place")
                    mbti_raw = cell_at(row_cells, "mbti")
                    gender_raw = cell_at(row_cells, "gender")

                    birth_date = _parse_birth_date(birth_raw)
                    birth_time, birth_time_unknown = _parse_birth_time(time_raw)

                    if len(people) < 15:
                        print(f"[SHEETS_DEBUG] #{len(people)} name={name!r} gender_raw={gender_raw!r} dept={department!r}")

                    people.append(
                        Person(
                            person_id=_make_person_id(department, name, birth_raw),
                            name=name,
                            category=PersonCategory.EMPLOYEE,
                            gender=_parse_gender(gender_raw),
                            birth_date=birth_date,
                            birth_time=birth_time,
                            birth_time_unknown=birth_time_unknown,
                            birth_prefecture=place_raw,
                            department=department,
                            mbti=mbti_raw,
                            status="在籍",
                            retention=RetentionInfo(retention_policy="manual"),
                            sheet_row_ref=f"{BIRTHDAY_SHEET_NAME}!R{data_row + 1}C{c + 1}",
                        )
                    )
                    data_row += 1
        return people

    def search_people(self, query: PersonSearchQuery) -> list[Person]:
        people = self._parse_all()
        results = people
        if query.name_query:
            q = _norm_name(query.name_query)
            results = [p for p in results if q in _norm_name(p.name)]
        if query.department:
            results = [p for p in results if query.department in p.department]
        if query.category:
            results = [p for p in results if p.category == query.category]
        return results[: query.limit]

    def get_person(self, person_id: UUID) -> Person | None:
        for p in self._parse_all():
            if p.person_id == person_id:
                return p
        return None

    def find_by_name(self, name: str) -> list[Person]:
        target = _norm_name(name)
        return [p for p in self._parse_all() if _norm_name(p.name) == target or target in _norm_name(p.name)]

    def list_all(self) -> list[Person]:
        return self._parse_all()

    def create_person(self, person: Person) -> Person:
        raise SheetsWriteNotSupportedError(
            "現在は「生年月日」シートの参照のみに対応しており、新規登録はできません。"
        )

    def update_person_fields(self, person_id: UUID, changes: dict) -> Person:
        raise SheetsWriteNotSupportedError(
            "現在は「生年月日」シートの参照のみに対応しており、情報の更新はできません。"
        )

    def append_interview_note(self, person_id: UUID, note_content: str, author_line_user_id: str,
                               occurred_on: date, sensitive_tags: list[str]) -> Person:
        raise SheetsWriteNotSupportedError(
            "現在は「生年月日」シートの参照のみに対応しており、面談記録の保存はできません。"
        )

    def soft_delete(self, person_id: UUID) -> Person:
        raise SheetsWriteNotSupportedError(
            "現在は「生年月日」シートの参照のみに対応しており、削除はできません。"
        )

    def remove_last_interview_note(self, person_id: UUID) -> Person:
        raise SheetsWriteNotSupportedError(
            "現在は「生年月日」シートの参照のみに対応しており、この操作はできません。"
        )

    def restore(self, person_id: UUID) -> Person:
        raise SheetsWriteNotSupportedError(
            "現在は「生年月日」シートの参照のみに対応しており、この操作はできません。"
        )

    def mark_interview_note_deleted(self, person_id: UUID, note_id) -> Person:
        raise SheetsWriteNotSupportedError(
            "現在は「生年月日」シートの参照のみに対応しており、この操作はできません。"
        )


def get_person_repository():
    """設定に応じてモック/本番実装を返すファクトリ。"""
    settings = get_settings()
    if settings.google_sheets_mode.value == "live":
        return GoogleSheetsPersonRepository()
    from app.sheets.mock_repository import MockPersonRepository

    return MockPersonRepository()
