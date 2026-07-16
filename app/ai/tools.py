"""Claude APIに渡すツール定義（JSON Schema、厳密なスキーマ検証込み）。
書き込み系ツールはClaudeの判断だけで実行されず、app/ai/tool_executor.py が
権限・入力検証・確認・監査ログを経てから app/services/ を呼び出す。
"""
from __future__ import annotations

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "search_people",
        "description": "氏名・部署・区分で人物を検索する。表記揺れにもある程度対応する。",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_query": {"type": "string", "description": "氏名またはフリガナの一部"},
                "category": {
                    "type": "string",
                    "enum": ["employee", "candidate", "external_consultant", "business_partner", "instructor", "partner", "other"],
                },
                "department": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_person_profile",
        "description": "person_idを指定して人物の基本プロフィールを取得する（機微情報は含まない）。",
        "input_schema": {
            "type": "object",
            "properties": {"person_id": {"type": "string"}},
            "required": ["person_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_relevant_hr_context",
        "description": "質問の目的に応じて必要最小限の人事情報（面談記録・評価・希望キャリア等）を取得する。健康・家族・退職相談情報は目的がretention_riskの場合のみ含まれる可能性がある。",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_id": {"type": "string"},
                "purpose": {
                    "type": "string",
                    "enum": ["fortune_only", "simple_analysis", "detailed_analysis", "compatibility",
                             "interview_prep", "retention_risk", "candidate_screening"],
                },
            },
            "required": ["person_id", "purpose"],
            "additionalProperties": False,
        },
    },
    {
        "name": "calculate_four_pillars",
        "description": "person_idの四柱推命・陰陽五行の構造化結果を取得する（決定論的計算エンジンによる。LLMは推測しない）。",
        "input_schema": {
            "type": "object",
            "properties": {"person_id": {"type": "string"}},
            "required": ["person_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "calculate_sanmeigaku",
        "description": "person_idの算命学の構造化結果（中心星・十大主星・十二大従星・天中殺等）を取得する。",
        "input_schema": {
            "type": "object",
            "properties": {"person_id": {"type": "string"}},
            "required": ["person_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_luck_cycles",
        "description": "person_idの大運・年運・月運を取得する。",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_id": {"type": "string"},
                "annual_year": {"type": "integer", "description": "年運を確認したい西暦年（任意）"},
                "monthly_date": {"type": "string", "description": "月運を確認したい日付 YYYY-MM-DD（任意）"},
            },
            "required": ["person_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "register_person",
        "description": "新しい人物を登録する。実行前に必ずユーザーへ確認済みであること（confirmedがtrueの場合のみ実行される）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "category": {
                    "type": "string",
                    "enum": ["employee", "candidate", "external_consultant", "business_partner", "instructor", "partner", "other"],
                },
                "gender": {"type": "string", "enum": ["male", "female", "other", "unknown"]},
                "birth_date": {"type": "string", "description": "YYYY-MM-DD"},
                "birth_time": {"type": "string", "description": "HH:MM（不明な場合は省略）"},
                "birth_time_unknown": {"type": "boolean"},
                "prefecture": {"type": "string"},
                "city": {"type": "string"},
                "confirmed": {"type": "boolean", "description": "ユーザーが最終確認済みかどうか"},
                "raw_input_text": {"type": "string"},
            },
            "required": ["name", "category", "gender", "birth_date", "confirmed", "raw_input_text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "prepare_person_update",
        "description": "基本情報の変更案を作成し、確認待ち状態にする（即時反映しない）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_id": {"type": "string"},
                "changes": {"type": "object", "description": "変更したいフィールドと新しい値"},
                "raw_input_text": {"type": "string"},
            },
            "required": ["person_id", "changes", "raw_input_text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "confirm_person_update",
        "description": "確認待ちの変更を確定して反映する。",
        "input_schema": {
            "type": "object",
            "properties": {
                "pending_operation_id": {"type": "string"},
                "approved": {"type": "boolean"},
            },
            "required": ["pending_operation_id", "approved"],
            "additionalProperties": False,
        },
    },
    {
        "name": "append_interview_note",
        "description": "面談記録を追記する（上書きせず日付ごとに追加、確認なしで保存可）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_id": {"type": "string"},
                "occurred_on": {"type": "string", "description": "YYYY-MM-DD"},
                "content": {"type": "string"},
                "sensitive_tags": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["health", "family", "retirement_consultation", "other_sensitive"]},
                },
                "raw_input_text": {"type": "string"},
            },
            "required": ["person_id", "occurred_on", "content", "raw_input_text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "compare_people",
        "description": "【第2段階で実装予定】複数人を比較する。MVPでは未実装の案内を返す。",
        "input_schema": {
            "type": "object",
            "properties": {"person_ids": {"type": "array", "items": {"type": "string"}}},
            "required": ["person_ids"],
            "additionalProperties": False,
        },
    },
    {
        "name": "analyze_team",
        "description": "【第2段階で実装予定】チーム編成を分析する。MVPでは未実装の案内を返す。",
        "input_schema": {
            "type": "object",
            "properties": {"person_ids": {"type": "array", "items": {"type": "string"}}},
            "required": ["person_ids"],
            "additionalProperties": False,
        },
    },
    {
        "name": "undo_last_change",
        "description": "直前の変更操作を取り消す。取り消し可能期限内のもののみ対象。",
        "input_schema": {
            "type": "object",
            "properties": {"target_person_id": {"type": "string", "description": "省略時は全体の直前操作"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "soft_delete_record",
        "description": "人物レコードまたは面談記録を論理削除する。実行前に必ず確認済みであること。",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_id": {"type": "string"},
                "confirmed": {"type": "boolean"},
                "raw_input_text": {"type": "string"},
            },
            "required": ["person_id", "confirmed", "raw_input_text"],
            "additionalProperties": False,
        },
    },
]

WRITE_TOOL_NAMES = {
    "register_person",
    "prepare_person_update",
    "confirm_person_update",
    "append_interview_note",
    "soft_delete_record",
    "undo_last_change",
}
