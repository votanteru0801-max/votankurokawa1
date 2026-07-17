"""会話オーケストレーター。LINEユーザーからのメッセージ1件を受け取り、
会話状態(DB)・決定論的な登録/更新/削除フロー・命式計算・AI分析生成を
組み合わせて、LINEへ送る応答メッセージ一覧を返す。

安全設計の要点:
- 書き込み（登録・基本情報変更・削除）は必ず確認ステップを経る
  （面談記録の追記のみポリシー上、確認なしで保存する）。
- 対象人物の特定はアプリ側の決定論的なロジックで行い、Claudeに委ねない。
- Claude(またはモック)は命式計算結果と最小化された人事情報を渡された上での
  「解釈・文章化」のみを担当する。
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, time
from uuid import UUID

from app.ai.client_interface import AnalysisGenerationError
from app.ai.prompt_design import DataPurpose
from app.ai.response_formatter import format_detailed_analysis, format_simple_analysis
from app.ai.tool_executor import ToolContext, ToolValidationError, execute_tool
from app.config import get_settings
from app.line import nl_update_parser
from app.line.messaging import prepare_reply_messages
from app.line.nl_registration_parser import ParsedRegistration, parse_bulk_registration_text
from app.schemas.person import Gender, PersonCategory
from app.services import audit_service, conversation_service, interview_service, person_service
from app.sheets.interface import PersonRepository

FIELD_LABELS = {
    "position": "役職",
    "department": "部署",
    "mbti": "MBTI",
    "birth_date": "生年月日",
    "birth_time": "出生時間",
    "birth_prefecture": "出生地",
    "gender": "性別",
    "status": "在籍状況",
    "desired_career": "希望キャリア",
}

SENSITIVE_CONFIRM_FIELDS = {"birth_date", "birth_time", "birth_prefecture", "gender"}


def _field_label(field_name: str) -> str:
    return FIELD_LABELS.get(field_name, field_name)


def _parsed_to_dict(p: ParsedRegistration) -> dict:
    d = asdict(p)
    d["category"] = p.category.value if p.category else None
    d["gender"] = p.gender.value if p.gender else Gender.UNKNOWN.value
    d["birth_date"] = p.birth_date.isoformat() if p.birth_date else None
    d["birth_time"] = p.birth_time.isoformat() if p.birth_time else None
    return d


def _dict_to_parsed(d: dict) -> ParsedRegistration:
    return ParsedRegistration(
        category=PersonCategory(d["category"]) if d.get("category") else None,
        name=d.get("name"),
        birth_date=date.fromisoformat(d["birth_date"]) if d.get("birth_date") else None,
        birth_time=time.fromisoformat(d["birth_time"]) if d.get("birth_time") else None,
        birth_time_unknown=d.get("birth_time_unknown", True),
        prefecture=d.get("prefecture"),
        city=d.get("city"),
        gender=Gender(d.get("gender", "unknown")),
        unparsed_tokens=d.get("unparsed_tokens", []),
    )


def _looks_like_bulk_registration(text: str) -> bool:
    if "登録" not in text:
        return False
    if (text.count("、") + text.count(",")) >= 1:
        return True
    from app.line.nl_registration_parser import CATEGORY_KEYWORDS, DATE_RE

    if DATE_RE.search(text):
        return True
    return any(kw in text for kw in CATEGORY_KEYWORDS)


def _detect_analysis_mode(text: str) -> str | None:
    if "詳細" in text and ("分析" in text or "教えて" in text):
        return "detailed"
    if "簡易" in text and "分析" in text:
        return "simple"
    if any(k in text for k in ("分析して", "教えて", "強み", "弱み", "命式", "適性")):
        return "simple"
    return None


def _norm_for_match(s: str) -> str:
    """氏名照合用の正規化。全角・半角スペースの有無による表記揺れ
    （例:「濱澤ひかり」/「濱澤 ひかり」）を吸収する。"""
    return (s or "").replace("　", "").replace(" ", "")


def _extract_person_name(repo: PersonRepository, text: str) -> str | None:
    names = sorted((p.name for p in repo.list_all()), key=len, reverse=True)
    norm_text = _norm_for_match(text)
    for name in names:
        if name and _norm_for_match(name) in norm_text:
            return name
    return None


def _resolve_candidate_choice(repo: PersonRepository, candidate_ids: list[str], text: str):
    text = text.strip()
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(candidate_ids):
            return repo.get_person(UUID(candidate_ids[idx]))
    for cid in candidate_ids:
        person = repo.get_person(UUID(cid))
        if person and person.name in text:
            return person
    return None


class Orchestrator:
    def __init__(self, db: Session, repo: PersonRepository, ai_client) -> None:
        self.db = db
        self.repo = repo
        self.ai_client = ai_client

    def handle_message(self, line_user_id: str, text: str, line_event_id: str) -> list[str]:
        text = text.strip()
        state = conversation_service.get_state(self.db, line_user_id)

        handlers = {
            "registration_qa": self._continue_registration_qa,
            "registration_confirm": self._handle_registration_confirm,
            "duplicate_disambiguation": self._handle_duplicate_disambiguation,
            "update_confirm": self._handle_update_confirm,
            "update_disambiguation": self._handle_update_disambiguation,
            "interview_note_awaiting_content": self._handle_interview_note_content,
            "interview_note_disambiguation": self._handle_interview_note_disambiguation,
            "delete_note_person_disambiguation": self._handle_delete_note_disambiguation,
            "analysis_disambiguation": self._handle_analysis_disambiguation,
            "awaiting_analysis_person_name": self._handle_awaiting_analysis_person_name,
            "awaiting_interview_person_name": self._handle_awaiting_interview_person_name,
        }
        if state.state_type in handlers:
            return handlers[state.state_type](line_user_id, text, state, line_event_id)

        return self._handle_idle(line_user_id, text, line_event_id)

    # ---- idle: トップレベルの意図判定 ----
    def _handle_idle(self, line_user_id: str, text: str, line_event_id: str) -> list[str]:
        cmd = nl_update_parser.parse_update_command(text)

        if cmd.kind == "undo":
            ctx = ToolContext(line_user_id, self.db, self.repo)
            result = execute_tool("undo_last_change", {}, ctx)
            if result["status"] == "undone":
                return [f"直前の操作（{result['operation_type']}）を取り消しました。"]
            return [result.get("message", "取り消せる操作がありません。")]

        if cmd.kind == "delete_interview_note":
            return self._handle_delete_interview_note(line_user_id, text, cmd)

        if cmd.kind == "interview_note":
            return self._handle_interview_note_start(line_user_id, cmd)

        if cmd.kind in ("career_append", "basic_field_update"):
            return self._handle_basic_update_start(line_user_id, cmd)

        if text in ("人物を登録",):
            return self._start_qa_registration(line_user_id)

        if text in ("面談を記録",):
            conversation_service.set_state(self.db, line_user_id, "awaiting_interview_person_name", {})
            return ["どなたとの面談内容を記録しますか？氏名を教えてください。"]

        if text in ("簡易分析", "詳細分析"):
            mode = "detailed" if text == "詳細分析" else "simple"
            conversation_service.set_state(self.db, line_user_id, "awaiting_analysis_person_name", {"mode": mode})
            return ["どなたについて分析しますか？氏名を教えてください。"]

        if _looks_like_bulk_registration(text):
            return self._start_bulk_registration(line_user_id, text)

        if text in ("相性分析", "人材を比較"):
            return ["この機能は第2段階で実装予定です。現在はご利用いただけません（docs/phase2-design.md）。"]

        mode = _detect_analysis_mode(text)
        if mode:
            return self._handle_analysis(line_user_id, text, mode)

        return ["すみません、うまく理解できませんでした。「簡易分析」「詳細分析」「人物を登録」などでお試しください。"]

    # ---- 登録: 一括入力 ----
    def _start_bulk_registration(self, line_user_id: str, text: str) -> list[str]:
        parsed = parse_bulk_registration_text(text)
        missing = parsed.missing_required_fields()
        if missing:
            conversation_service.set_state(
                self.db, line_user_id, "registration_qa",
                {"parsed": _parsed_to_dict(parsed), "asked": [], "current_field": None},
            )
            next_field = person_service.next_missing_question_field(parsed, set())
            conversation_service.set_state(
                self.db, line_user_id, "registration_qa",
                {"parsed": _parsed_to_dict(parsed), "asked": [], "current_field": next_field},
            )
            return [
                f"以下の情報が不足しています: {', '.join(missing)}",
                person_service.QUESTION_TEXT[next_field],
            ]
        return self._after_registration_parsed(line_user_id, parsed, text)

    def _start_qa_registration(self, line_user_id: str) -> list[str]:
        parsed = ParsedRegistration()
        conversation_service.set_state(
            self.db, line_user_id, "registration_qa",
            {"parsed": _parsed_to_dict(parsed), "asked": [], "current_field": "category"},
        )
        return [person_service.QUESTION_TEXT["category"]]

    def _continue_registration_qa(self, line_user_id, text, state, line_event_id) -> list[str]:
        data = state.state_data
        parsed = _dict_to_parsed(data["parsed"])
        asked = set(data.get("asked", []))
        current_field = data.get("current_field")

        if text in ("中止", "中止する", "やめる"):
            conversation_service.clear_state(self.db, line_user_id)
            return ["登録を中止しました。"]

        if current_field:
            parsed = person_service.apply_answer(parsed, current_field, text)
            asked.add(current_field)

        next_field = person_service.next_missing_question_field(parsed, asked)
        if next_field:
            conversation_service.set_state(
                self.db, line_user_id, "registration_qa",
                {"parsed": _parsed_to_dict(parsed), "asked": list(asked), "current_field": next_field},
            )
            return [person_service.QUESTION_TEXT[next_field]]

        missing = parsed.missing_required_fields()
        if missing:
            conversation_service.clear_state(self.db, line_user_id)
            return [f"登録に必要な情報が不足しています: {', '.join(missing)}。お手数ですが最初からやり直してください。"]

        return self._after_registration_parsed(line_user_id, parsed, "(質問形式で登録)")

    def _after_registration_parsed(self, line_user_id, parsed: ParsedRegistration, raw_text: str) -> list[str]:
        dups = person_service.check_duplicates(self.repo, parsed.name)
        if dups:
            conversation_service.set_state(
                self.db, line_user_id, "duplicate_disambiguation",
                {"parsed": _parsed_to_dict(parsed), "raw_text": raw_text},
            )
            return [
                person_service.build_disambiguation_message(dups)
                + "\n\n新規の別人として登録する場合は「新規登録」、中止する場合は「中止する」とお答えください。"
            ]
        conversation_service.set_state(
            self.db, line_user_id, "registration_confirm",
            {"parsed": _parsed_to_dict(parsed), "raw_text": raw_text},
        )
        return [person_service.build_confirmation_message(parsed)]

    def _handle_registration_confirm(self, line_user_id, text, state, line_event_id) -> list[str]:
        parsed = _dict_to_parsed(state.state_data["parsed"])
        raw_text = state.state_data.get("raw_text", "")
        if text in ("登録する", "登録", "はい", "OK", "ok"):
            person = person_service.register_confirmed(self.repo, self.db, line_user_id, parsed, raw_text)
            conversation_service.clear_state(self.db, line_user_id)
            return [f"{person.name}さんを登録しました。"]
        if text in ("中止する", "中止", "やめる"):
            conversation_service.clear_state(self.db, line_user_id)
            return ["登録を中止しました。"]
        if text in ("修正する", "修正"):
            conversation_service.set_state(
                self.db, line_user_id, "registration_qa",
                {"parsed": _parsed_to_dict(parsed), "asked": [], "current_field": "category"},
            )
            return ["最初の項目から修正します。", person_service.QUESTION_TEXT["category"]]
        return ["「登録する」「修正する」「中止する」のいずれかでお答えください。"]

    def _handle_duplicate_disambiguation(self, line_user_id, text, state, line_event_id) -> list[str]:
        parsed = _dict_to_parsed(state.state_data["parsed"])
        raw_text = state.state_data.get("raw_text", "")
        if any(k in text for k in ("新規登録", "別人", "新規で")):
            conversation_service.set_state(
                self.db, line_user_id, "registration_confirm",
                {"parsed": _parsed_to_dict(parsed), "raw_text": raw_text},
            )
            return [person_service.build_confirmation_message(parsed)]
        if text in ("中止", "中止する", "やめる"):
            conversation_service.clear_state(self.db, line_user_id)
            return ["登録を中止しました。"]
        return [
            "新規の別人として登録する場合は「新規登録」、中止する場合は「中止する」とお答えください。"
        ]

    # ---- 基本情報更新 ----
    def _handle_basic_update_start(self, line_user_id: str, cmd: nl_update_parser.ParsedCommand) -> list[str]:
        person, candidates = person_service.resolve_person_by_name(self.repo, cmd.person_name)
        if person is None and candidates:
            conversation_service.set_state(
                self.db, line_user_id, "update_disambiguation",
                {"cmd": {"kind": cmd.kind, "field": cmd.field_name, "value": cmd.value},
                 "candidates": [str(c.person_id) for c in candidates]},
            )
            return [person_service.build_disambiguation_message(candidates)]
        if person is None:
            return [f"「{cmd.person_name}」に該当する人物が見つかりませんでした。"]
        return self._prepare_update_confirmation(line_user_id, person, cmd.kind, cmd.field_name, cmd.value)

    def _prepare_update_confirmation(self, line_user_id, person, kind, field_name, value) -> list[str]:
        before = getattr(person, field_name)
        before_str = before.isoformat() if hasattr(before, "isoformat") else str(before)
        if kind == "career_append":
            after_str = f"{before_str}\n{value}" if before_str and before_str != "None" else value
        else:
            after_str = value
        conversation_service.set_state(
            self.db, line_user_id, "update_confirm",
            {
                "person_id": str(person.person_id),
                "field": field_name,
                "before": before_str,
                "after": after_str,
                "raw_input_text": f"{person.name}の{_field_label(field_name)}を{value}に変更",
            },
        )
        caution = ""
        if field_name in SENSITIVE_CONFIRM_FIELDS:
            caution = "（生年月日・出生時間・出生地・性別の変更は命式の再計算に影響します）"
        return [
            f"{person.name}さんの{_field_label(field_name)}を「{before_str}」から「{after_str}」に変更します{caution}。"
            "よろしいですか？「変更する」「中止する」でお答えください。"
        ]

    def _handle_update_disambiguation(self, line_user_id, text, state, line_event_id) -> list[str]:
        candidates = state.state_data["candidates"]
        person = _resolve_candidate_choice(self.repo, candidates, text)
        if person is None:
            return ["番号または氏名でお答えください。"]
        cmd_data = state.state_data["cmd"]
        return self._prepare_update_confirmation(line_user_id, person, cmd_data["kind"], cmd_data["field"], cmd_data["value"])

    def _handle_update_confirm(self, line_user_id, text, state, line_event_id) -> list[str]:
        data = state.state_data
        if text in ("変更する", "はい", "OK", "ok"):
            person = self.repo.get_person(UUID(data["person_id"]))
            updated = person_service.confirm_basic_info_update(
                self.repo, self.db, line_user_id, person, data["field"], data["before"], data["after"], data["raw_input_text"]
            )
            conversation_service.clear_state(self.db, line_user_id)
            return [f"{updated.name}さんの{_field_label(data['field'])}を更新しました。"]
        if text in ("中止する", "中止", "やめる"):
            conversation_service.clear_state(self.db, line_user_id)
            return ["変更を中止しました。"]
        return ["「変更する」「中止する」のいずれかでお答えください。"]

    # ---- 面談記録 ----
    def _handle_interview_note_start(self, line_user_id: str, cmd: nl_update_parser.ParsedCommand) -> list[str]:
        person, candidates = person_service.resolve_person_by_name(self.repo, cmd.person_name)
        if person is None and candidates:
            conversation_service.set_state(
                self.db, line_user_id, "interview_note_disambiguation",
                {"content": cmd.content, "candidates": [str(c.person_id) for c in candidates]},
            )
            return [person_service.build_disambiguation_message(candidates)]
        if person is None:
            return [f"「{cmd.person_name}」に該当する人物が見つかりませんでした。"]
        if cmd.content:
            return self._save_interview_note(line_user_id, person, cmd.content)
        conversation_service.set_state(self.db, line_user_id, "interview_note_awaiting_content", {"person_id": str(person.person_id)})
        return ["面談内容を教えてください。"]

    def _handle_interview_note_disambiguation(self, line_user_id, text, state, line_event_id) -> list[str]:
        candidates = state.state_data["candidates"]
        person = _resolve_candidate_choice(self.repo, candidates, text)
        if person is None:
            return ["番号または氏名でお答えください。"]
        content = state.state_data.get("content")
        if content:
            return self._save_interview_note(line_user_id, person, content)
        conversation_service.set_state(self.db, line_user_id, "interview_note_awaiting_content", {"person_id": str(person.person_id)})
        return ["面談内容を教えてください。"]

    def _handle_interview_note_content(self, line_user_id, text, state, line_event_id) -> list[str]:
        person = self.repo.get_person(UUID(state.state_data["person_id"]))
        return self._save_interview_note(line_user_id, person, text)

    def _handle_awaiting_interview_person_name(self, line_user_id, text, state, line_event_id) -> list[str]:
        person, candidates = person_service.resolve_person_by_name(self.repo, text)
        if person is None and candidates:
            conversation_service.set_state(
                self.db, line_user_id, "interview_note_disambiguation",
                {"content": None, "candidates": [str(c.person_id) for c in candidates]},
            )
            return [person_service.build_disambiguation_message(candidates)]
        if person is None:
            return [f"「{text}」に該当する人物が見つかりませんでした。氏名を教えてください。"]
        conversation_service.set_state(self.db, line_user_id, "interview_note_awaiting_content", {"person_id": str(person.person_id)})
        return ["面談内容を教えてください。"]

    def _handle_awaiting_analysis_person_name(self, line_user_id, text, state, line_event_id) -> list[str]:
        mode = state.state_data["mode"]
        person, candidates = person_service.resolve_person_by_name(self.repo, text)
        if person is None and candidates:
            conversation_service.set_state(
                self.db, line_user_id, "analysis_disambiguation",
                {"mode": mode, "question": f"{mode}分析", "candidates": [str(c.person_id) for c in candidates]},
            )
            return [person_service.build_disambiguation_message(candidates)]
        if person is None:
            return [f"「{text}」に該当する人物が見つかりませんでした。氏名を教えてください。"]
        conversation_service.clear_state(self.db, line_user_id)
        return self._run_analysis_for_person(line_user_id, person, f"{person.name}の{mode}分析", mode)

    def _save_interview_note(self, line_user_id, person, content: str) -> list[str]:
        interview_service.append_note(
            self.repo, self.db, line_user_id, person, content, date.today(), [], f"面談記録: {content}"
        )
        conversation_service.clear_state(self.db, line_user_id)
        return [f"{person.name}さんとの面談内容を記録しました。"]

    def _handle_delete_interview_note(self, line_user_id, text, cmd) -> list[str]:
        year = date.today().year
        try:
            target_date = date(year, cmd.extra["month"], cmd.extra["day"])
        except ValueError:
            return ["日付が正しくありません。"]
        matches = [p for p in self.repo.list_all() if any(n.occurred_on == target_date and not n.deleted for n in p.interview_notes)]
        if not matches:
            return [f"{target_date.isoformat()}の面談記録が見つかりませんでした。"]
        if len(matches) > 1:
            conversation_service.set_state(
                self.db, line_user_id, "delete_note_person_disambiguation",
                {"month": cmd.extra["month"], "day": cmd.extra["day"], "candidates": [str(p.person_id) for p in matches]},
            )
            return [person_service.build_disambiguation_message(matches) + "\n\nどなたの面談記録を削除しますか？"]
        _, msg = interview_service.delete_note_by_date(self.repo, self.db, line_user_id, matches[0], target_date, text)
        return [msg]

    def _handle_delete_note_disambiguation(self, line_user_id, text, state, line_event_id) -> list[str]:
        candidates = state.state_data["candidates"]
        person = _resolve_candidate_choice(self.repo, candidates, text)
        if person is None:
            return ["番号または氏名でお答えください。"]
        target_date = date(date.today().year, state.state_data["month"], state.state_data["day"])
        conversation_service.clear_state(self.db, line_user_id)
        _, msg = interview_service.delete_note_by_date(self.repo, self.db, line_user_id, person, target_date, text)
        return [msg]

    # ---- 分析 ----
    def _handle_analysis(self, line_user_id: str, text: str, mode: str) -> list[str]:
        person_name = _extract_person_name(self.repo, text)
        if person_name is None:
            return ["対象の人物名を認識できませんでした。氏名を含めて質問してください。"]
        person, candidates = person_service.resolve_person_by_name(self.repo, person_name)
        if person is None and candidates:
            conversation_service.set_state(
                self.db, line_user_id, "analysis_disambiguation",
                {"mode": mode, "question": text, "candidates": [str(c.person_id) for c in candidates]},
            )
            return [person_service.build_disambiguation_message(candidates)]
        if person is None:
            return [f"「{person_name}」に該当する人物が見つかりませんでした。"]
        return self._run_analysis_for_person(line_user_id, person, text, mode)

    def _handle_analysis_disambiguation(self, line_user_id, text, state, line_event_id) -> list[str]:
        candidates = state.state_data["candidates"]
        person = _resolve_candidate_choice(self.repo, candidates, text)
        if person is None:
            return ["番号または氏名でお答えください。"]
        mode = state.state_data["mode"]
        question = state.state_data["question"]
        conversation_service.clear_state(self.db, line_user_id)
        return self._run_analysis_for_person(line_user_id, person, question, mode)

    def _run_analysis_for_person(self, line_user_id: str, person, question: str, mode: str) -> list[str]:
        ctx = ToolContext(line_user_id, self.db, self.repo)
        try:
            four_pillars = execute_tool("calculate_four_pillars", {"person_id": str(person.person_id)}, ctx)
            sanmeigaku = execute_tool("calculate_sanmeigaku", {"person_id": str(person.person_id)}, ctx)
            luck = execute_tool(
                "get_luck_cycles", {"person_id": str(person.person_id), "annual_year": date.today().year}, ctx
            )
        except ToolValidationError as e:
            return [f"命式計算でエラーが発生しました: {e}"]

        calculation_data = {"shichuu_suimei": four_pillars, "sanmeigaku": sanmeigaku, "luck_cycles": luck}
        purpose = DataPurpose.DETAILED_ANALYSIS if mode == "detailed" else DataPurpose.SIMPLE_ANALYSIS
        hr_context = execute_tool(
            "get_relevant_hr_context", {"person_id": str(person.person_id), "purpose": purpose.value}, ctx
        )

        accuracy_notes = list(four_pillars.get("hour_pillar_omitted_reason") and [four_pillars["hour_pillar_omitted_reason"]] or [])

        try:
            resp = self.ai_client.generate_analysis(
                mode, person.name, str(person.person_id), calculation_data, hr_context, question, accuracy_notes
            )
        except AnalysisGenerationError:
            return ["AI分析の生成に失敗しました。時間をおいて再度お試しください。"]

        settings = get_settings()
        audit_service.log_ai_request(
            self.db, line_user_id, intent=f"{mode}_analysis",
            tool_calls={"calculate_four_pillars": 1, "calculate_sanmeigaku": 1, "get_luck_cycles": 1},
            data_sent_summary={"fields": list(hr_context.keys())},
            model=settings.anthropic_model,
        )

        formatted = format_detailed_analysis(resp) if mode == "detailed" else format_simple_analysis(resp)
        return prepare_reply_messages(formatted)
