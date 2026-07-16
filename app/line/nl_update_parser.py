"""更新・面談記録・取り消し系の自然文コマンドを解釈する簡易パーサー（規則ベース）。

register同様、ANTHROPIC_MODE=liveではClaudeのNLUが主経路となりうるが、
mockモードでの動作・自動テストのため決定論的な実装を用意する。
表記揺れをすべて拾いきれるわけではなく、認識できない場合は
ParsedCommand(kind="unrecognized")を返し、上位層でAIフォールバックまたは
再質問を行う。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

FIELD_LABEL_TO_PERSON_FIELD = {
    "役職": "position",
    "部署": "department",
    "所属": "department",
    "MBTI": "mbti",
    "生年月日": "birth_date",
    "出生時間": "birth_time",
    "出生地": "birth_prefecture",
    "性別": "gender",
    "在籍状況": "status",
    "状態": "status",
}

UNDO_PATTERNS = [
    re.compile(r"直前の変更を?取り消して"),
    re.compile(r"さっき変更した.*を元に戻して"),
    re.compile(r"今の変更を取り消して"),
]

INTERVIEW_NOTE_PATTERNS = [
    re.compile(r"(?:今日の)?(?P<name>[^\s、。]+?)との面談(?:内容|記録)を(?:記録|保存)して[:：]?(?P<content>.*)"),
    re.compile(r"(?P<name>[^\s、。]+?)の面談記録に(?P<content>.+?)を追加して"),
]

CAREER_APPEND_PATTERN = re.compile(
    r"(?P<name>[^\s、。]+?)の(?:希望キャリア|キャリア希望)に、?(?P<value>.+?)と?追加して"
)

BASIC_FIELD_UPDATE_PATTERN = re.compile(
    r"(?P<name>[^\s、。]+?)の(?P<field>役職|部署|所属|MBTI|生年月日|出生時間|出生地|性別|在籍状況|状態)を(?P<value>.+?)に変更して"
)

DELETE_INTERVIEW_NOTE_PATTERN = re.compile(r"(?P<month>\d{1,2})月(?P<day>\d{1,2})日の面談記録を削除して")


@dataclass
class ParsedCommand:
    kind: str  # undo | interview_note | career_append | basic_field_update | delete_interview_note | unrecognized
    person_name: str | None = None
    field_name: str | None = None
    value: str | None = None
    content: str | None = None
    extra: dict = field(default_factory=dict)


def parse_update_command(text: str) -> ParsedCommand:
    for pat in UNDO_PATTERNS:
        if pat.search(text):
            return ParsedCommand(kind="undo")

    m = DELETE_INTERVIEW_NOTE_PATTERN.search(text)
    if m:
        return ParsedCommand(
            kind="delete_interview_note", extra={"month": int(m.group("month")), "day": int(m.group("day"))}
        )

    for pat in INTERVIEW_NOTE_PATTERNS:
        m = pat.search(text)
        if m:
            content = m.group("content").strip(" :：。")
            return ParsedCommand(kind="interview_note", person_name=m.group("name"), content=content or None)

    m = CAREER_APPEND_PATTERN.search(text)
    if m:
        return ParsedCommand(
            kind="career_append", person_name=m.group("name"), field_name="desired_career", value=m.group("value").strip()
        )

    m = BASIC_FIELD_UPDATE_PATTERN.search(text)
    if m:
        field_name = FIELD_LABEL_TO_PERSON_FIELD.get(m.group("field"))
        if field_name:
            return ParsedCommand(
                kind="basic_field_update", person_name=m.group("name"), field_name=field_name, value=m.group("value").strip()
            )

    return ParsedCommand(kind="unrecognized")
