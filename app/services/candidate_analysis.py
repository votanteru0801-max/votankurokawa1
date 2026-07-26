"""採用候補者（まだ社員名簿=スプレッドシートに存在しない人物）を、その場限りで
分析するためのロジック。

方針（ユーザー確認済み・2026-07-26）:
- 入力されたデータは一切保存しない（Firestoreにもスプレッドシートにも書き込まない）。
  電卓のように、その場で生年月日等を入力して分析結果を見るだけの使い切り機能。
- 既存の簡易/詳細分析（app/services/analysis_service.py）のロジックをそのまま流用し、
  一時的な人物オブジェクトだけをその1回のリクエストの間だけ「repo」として見せかける
  ことで、既存コードの変更を最小限にする。
"""
from __future__ import annotations

import uuid
from datetime import date, time

from app.schemas.person import Gender, Person, PersonCategory, RetentionInfo


class _EphemeralSingleRepo:
    """PersonRepository風の最小限のダック型ラッパー。
    分析処理の内部で get_person(person_id) しか呼ばれないため、それだけ実装する。
    候補者データはメモリ上に置くだけで、どこにも永続化しない。
    """

    def __init__(self, person: Person):
        self._person = person

    def get_person(self, person_id):
        if person_id == self._person.person_id:
            return self._person
        return None


class CandidateInputError(Exception):
    """ユーザーにそのまま見せてよい入力エラーメッセージを保持する。"""


_GENDER_MAP = {
    "male": Gender.MALE,
    "female": Gender.FEMALE,
    "other": Gender.OTHER,
    "unknown": Gender.UNKNOWN,
    "": Gender.UNKNOWN,
}


def build_candidate_person(fields: dict) -> Person:
    """Web画面から送られてきたフォーム値（dict）から、その場限りのPersonを組み立てる。
    生年月日は "YYYY-MM-DD" 形式必須。不正な場合は CandidateInputError を送出する。
    """
    name = (fields.get("name") or "").strip() or "候補者"
    birth_date_raw = (fields.get("birth_date") or "").strip()
    if not birth_date_raw:
        raise CandidateInputError("生年月日を入力してください。")
    try:
        birth_date = date.fromisoformat(birth_date_raw)
    except ValueError as e:
        raise CandidateInputError("生年月日の形式が正しくありません（例: 1998-04-07）。") from e

    birth_time_raw = (fields.get("birth_time") or "").strip()
    birth_time_unknown = bool(fields.get("birth_time_unknown")) or not birth_time_raw
    birth_time: time | None = None
    if birth_time_raw and not birth_time_unknown:
        try:
            birth_time = time.fromisoformat(birth_time_raw)
        except ValueError as e:
            raise CandidateInputError("出生時刻の形式が正しくありません（例: 14:30）。") from e

    gender_raw = (fields.get("gender") or "unknown").strip()
    gender = _GENDER_MAP.get(gender_raw, Gender.UNKNOWN)

    return Person(
        person_id=uuid.uuid4(),
        name=name,
        category=PersonCategory.CANDIDATE,
        gender=gender,
        birth_date=birth_date,
        birth_time=birth_time,
        birth_time_unknown=birth_time_unknown,
        birth_prefecture=(fields.get("prefecture") or "").strip(),
        mbti=(fields.get("mbti") or "").strip().upper(),
        status="選考中",
        retention=RetentionInfo(retention_policy="candidate_ephemeral_no_storage"),
    )


def run_candidate_analysis(db, ai_client, actor_id: str, fields: dict, mode: str) -> str:
    """候補者データを保存せずに簡易/詳細分析を実行し、整形済みテキストを返す。
    エラーはすべて呼び出し側にそのまま見せてよい例外として送出する
    （CandidateInputError または app.services.analysis_service.AnalysisError）。
    """
    from app.services.analysis_service import run_analysis_for_person

    candidate = build_candidate_person(fields)
    repo = _EphemeralSingleRepo(candidate)
    label = "詳細分析" if mode == "detailed" else "簡易分析"
    return run_analysis_for_person(db, repo, ai_client, actor_id, candidate, f"{candidate.name}の{label}", mode)
