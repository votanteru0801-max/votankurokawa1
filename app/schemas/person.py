"""人物情報スキーマ。Googleスプレッドシートを正本とするデータの内部表現。"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from enum import Enum

from pydantic import BaseModel, Field


class PersonCategory(str, Enum):
    EMPLOYEE = "employee"                    # 社員
    CANDIDATE = "candidate"                  # 採用候補者
    EXTERNAL_CONSULTANT = "external_consultant"  # 外部コンサルタント
    BUSINESS_PARTNER = "business_partner"    # 取引先
    INSTRUCTOR = "instructor"                # 講師
    PARTNER = "partner"                      # パートナー
    OTHER = "other"                          # その他


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class SensitiveTag(str, Enum):
    HEALTH = "health"                        # 健康・体調
    FAMILY = "family"                        # 家族事情
    RETIREMENT_CONSULTATION = "retirement_consultation"  # 退職相談
    OTHER_SENSITIVE = "other_sensitive"


class RetentionStatus(str, Enum):
    ACTIVE = "active"
    PENDING_DELETE = "pending_delete"
    SOFT_DELETED = "soft_deleted"


class InterviewNote(BaseModel):
    """面談記録。上書きせず日付ごとに追記する。"""

    note_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    occurred_on: date
    author_line_user_id: str
    content: str  # 原文。プロンプトとしては解釈しない「データ」として扱う
    sensitive_tags: list[SensitiveTag] = Field(default_factory=list)
    deleted: bool = False  # 論理削除（特定日の面談記録のみ削除する場合に使用）
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Evaluation(BaseModel):
    period: str  # 例: "2026年上期"
    summary: str
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class RetentionInfo(BaseModel):
    retention_policy: str  # 例: "candidate_6m_after_selection" / "employee_1y_after_resignation" / "manual"
    retention_start_date: date | None = None
    scheduled_delete_at: date | None = None
    legal_hold: bool = False
    deletion_status: RetentionStatus = RetentionStatus.ACTIVE


class Person(BaseModel):
    person_id: uuid.UUID = Field(default_factory=uuid.uuid4)

    # 基本情報
    name: str
    kana: str = ""
    aliases: list[str] = Field(default_factory=list)  # 旧姓・別名
    category: PersonCategory
    gender: Gender = Gender.UNKNOWN
    birth_date: date | None = None
    birth_time: time | None = None
    birth_time_unknown: bool = True
    birth_prefecture: str = ""
    birth_city: str = ""

    # 所属・職歴
    department: str = ""
    position: str = ""
    hire_date: date | None = None
    resignation_date: date | None = None
    status: str = ""  # 在籍/選考中/取引中/終了 等。値の意味は docs/data-dictionary.md 参照

    # 追加情報
    mbti: str = ""
    desired_career: str = ""
    evaluations: list[Evaluation] = Field(default_factory=list)
    interview_notes: list[InterviewNote] = Field(default_factory=list)
    retirement_consultation_notes: str = ""
    health_info: str = ""
    family_info: str = ""
    notes: str = ""

    retention: RetentionInfo

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    sheet_row_ref: str = ""  # スプレッドシート上の行参照（シート名!行番号など）


class PersonSearchQuery(BaseModel):
    name_query: str = ""
    category: PersonCategory | None = None
    department: str = ""
    limit: int = 20
