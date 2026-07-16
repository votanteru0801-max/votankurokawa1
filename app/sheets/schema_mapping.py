"""Googleスプレッドシートの列とPersonスキーマのマッピング層。

既存シートの列を削除・改名・並び替えしないという制約があるため、実際のシート
構成を確認するまでは「追加が必要な列」を仮の名称で定義しておき、
docs/current-sheet-schema.md の調査結果に基づいて調整する。

person_id は既存シートに存在しない前提のため、追加列として管理する。
"""
from __future__ import annotations

# シート名（人物区分ごとにシートを分けるか単一シートにするかは調査後に確定する。
# 現時点では単一シート「人物マスタ」を仮定し、person_id列を追加する設計とする）
PERSON_SHEET_NAME = "人物マスタ"

# 列名 -> Personフィールド名 の対応（仮）。実シート確認後にdocs/current-sheet-schema.mdへ
# 実際のヘッダーを記録し、本マッピングを更新すること。
COLUMN_TO_FIELD: dict[str, str] = {
    "person_id": "person_id",          # 追加列（内部ID、既存シートには無い前提）
    "氏名": "name",
    "フリガナ": "kana",
    "旧姓・別名": "aliases",
    "人物区分": "category",
    "性別": "gender",
    "生年月日": "birth_date",
    "出生時間": "birth_time",
    "出生時間不明": "birth_time_unknown",
    "出生都道府県": "birth_prefecture",
    "出生市区町村": "birth_city",
    "所属店舗・部署": "department",
    "現在の役職": "position",
    "入社日": "hire_date",
    "退職日": "resignation_date",
    "在籍・選考・取引状態": "status",
    "MBTI": "mbti",
    "本人の希望キャリア": "desired_career",
    "健康・体調情報": "health_info",
    "家族事情": "family_info",
    "備考": "notes",
    "登録日時": "created_at",
    "更新日時": "updated_at",
    # 保持ポリシー関連（追加列）
    "retention_policy": "retention.retention_policy",
    "retention_start_date": "retention.retention_start_date",
    "scheduled_delete_at": "retention.scheduled_delete_at",
    "legal_hold": "retention.legal_hold",
    "deletion_status": "retention.deletion_status",
}

# 評価・面談記録は別シート（追記型ログ）として管理する想定
INTERVIEW_NOTES_SHEET_NAME = "面談記録ログ"
EVALUATIONS_SHEET_NAME = "人事評価ログ"

FIELD_TO_COLUMN = {v: k for k, v in COLUMN_TO_FIELD.items()}
