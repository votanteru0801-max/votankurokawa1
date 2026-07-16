"""Claudeが呼び出すツールの実行層。
書き込み系ツールはここで権限・入力検証・確認・監査ログを必ず通してから
app/services/ を呼び出す。Claudeの判断だけでは絶対に書き込みを行わない。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import UUID

from app.calculation.engine import run_full_calculation
from app.calculation.policy import DEFAULT_POLICY
from app.calculation.schemas import BirthInput
from app.calculation.schemas import Gender as CalcGender
from app.line.nl_registration_parser import ParsedRegistration
from app.schemas.person import Gender, PersonCategory, PersonSearchQuery, SensitiveTag
from app.services import person_service
from app.ai.prompt_design import DataPurpose, minimize_person_context
from app.sheets.interface import PersonRepository


@dataclass
class ToolContext:
    line_user_id: str
    db: object
    repo: PersonRepository


class ToolValidationError(Exception):
    pass


def _get_person_or_error(ctx: ToolContext, person_id: str):
    try:
        pid = UUID(person_id)
    except ValueError as e:
        raise ToolValidationError("person_idの形式が不正です。") from e
    person = ctx.repo.get_person(pid)
    if person is None:
        raise ToolValidationError("該当する人物が見つかりませんでした。")
    return person


def _birth_input_from_person(person) -> BirthInput:
    gender_map = {
        Gender.MALE: CalcGender.MALE,
        Gender.FEMALE: CalcGender.FEMALE,
        Gender.OTHER: CalcGender.OTHER,
        Gender.UNKNOWN: CalcGender.UNKNOWN,
    }
    if person.birth_date is None:
        raise ToolValidationError("生年月日が未登録のため命式を計算できません。")
    return BirthInput(
        birth_date=person.birth_date,
        birth_time=person.birth_time,
        birth_time_unknown=person.birth_time_unknown,
        prefecture=person.birth_prefecture,
        city=person.birth_city,
        gender=gender_map.get(person.gender, CalcGender.UNKNOWN),
    )


def execute_tool(name: str, tool_input: dict, ctx: ToolContext) -> dict:
    if name == "search_people":
        query = PersonSearchQuery(
            name_query=tool_input.get("name_query", ""),
            category=PersonCategory(tool_input["category"]) if tool_input.get("category") else None,
            department=tool_input.get("department", ""),
        )
        results = ctx.repo.search_people(query)
        return {
            "results": [
                {"person_id": str(p.person_id), "name": p.name, "category": p.category.value, "department": p.department}
                for p in results
            ]
        }

    if name == "get_person_profile":
        person = _get_person_or_error(ctx, tool_input["person_id"])
        return minimize_person_context(person, DataPurpose.SIMPLE_ANALYSIS)

    if name == "get_relevant_hr_context":
        person = _get_person_or_error(ctx, tool_input["person_id"])
        purpose = DataPurpose(tool_input["purpose"])
        return minimize_person_context(person, purpose)

    if name == "calculate_four_pillars":
        person = _get_person_or_error(ctx, tool_input["person_id"])
        birth = _birth_input_from_person(person)
        result = run_full_calculation(birth, DEFAULT_POLICY)
        return result.shichuu_suimei.model_dump(mode="json")

    if name == "calculate_sanmeigaku":
        person = _get_person_or_error(ctx, tool_input["person_id"])
        birth = _birth_input_from_person(person)
        result = run_full_calculation(birth, DEFAULT_POLICY)
        return result.sanmeigaku.model_dump(mode="json")

    if name == "get_luck_cycles":
        person = _get_person_or_error(ctx, tool_input["person_id"])
        birth = _birth_input_from_person(person)
        annual_year = tool_input.get("annual_year")
        monthly_date = tool_input.get("monthly_date")
        result = run_full_calculation(
            birth,
            DEFAULT_POLICY,
            annual_start_year=annual_year,
            annual_count=3 if annual_year else 0,
            monthly_target=date.fromisoformat(monthly_date) if monthly_date else None,
        )
        return result.luck_cycles.model_dump(mode="json")

    if name == "register_person":
        if not tool_input.get("confirmed"):
            parsed = ParsedRegistration(
                category=PersonCategory(tool_input["category"]) if tool_input.get("category") else None,
                name=tool_input.get("name"),
                birth_date=date.fromisoformat(tool_input["birth_date"]) if tool_input.get("birth_date") else None,
                birth_time=time.fromisoformat(tool_input["birth_time"]) if tool_input.get("birth_time") else None,
                birth_time_unknown=tool_input.get("birth_time_unknown", not bool(tool_input.get("birth_time"))),
                prefecture=tool_input.get("prefecture"),
                city=tool_input.get("city"),
                gender=Gender(tool_input.get("gender", "unknown")),
            )
            missing = parsed.missing_required_fields()
            if missing:
                return {"status": "missing_fields", "missing": missing}
            dups = person_service.check_duplicates(ctx.repo, parsed.name)
            if dups:
                return {"status": "duplicate_check_required", "message": person_service.build_disambiguation_message(dups)}
            return {"status": "confirmation_required", "message": person_service.build_confirmation_message(parsed)}

        parsed = ParsedRegistration(
            category=PersonCategory(tool_input["category"]),
            name=tool_input["name"],
            birth_date=date.fromisoformat(tool_input["birth_date"]),
            birth_time=time.fromisoformat(tool_input["birth_time"]) if tool_input.get("birth_time") else None,
            birth_time_unknown=tool_input.get("birth_time_unknown", not bool(tool_input.get("birth_time"))),
            prefecture=tool_input.get("prefecture"),
            city=tool_input.get("city"),
            gender=Gender(tool_input.get("gender", "unknown")),
        )
        person = person_service.register_confirmed(
            ctx.repo, ctx.db, ctx.line_user_id, parsed, tool_input.get("raw_input_text", "")
        )
        return {"status": "registered", "person_id": str(person.person_id)}

    if name == "append_interview_note":
        person = _get_person_or_error(ctx, tool_input["person_id"])
        from app.services import interview_service

        tags = [SensitiveTag(t) for t in tool_input.get("sensitive_tags", [])]
        updated = interview_service.append_note(
            ctx.repo, ctx.db, ctx.line_user_id, person,
            tool_input["content"], date.fromisoformat(tool_input["occurred_on"]), tags,
            tool_input.get("raw_input_text", ""),
        )
        return {"status": "saved", "note_count": len(updated.interview_notes)}

    if name == "undo_last_change":
        from app.services import history_service

        try:
            change = history_service.undo_last_change(
                ctx.db, ctx.repo, ctx.line_user_id, tool_input.get("target_person_id")
            )
            return {"status": "undone", "operation_type": change.operation_type}
        except history_service.UndoNotAvailableError as e:
            return {"status": "unavailable", "message": str(e)}

    if name == "soft_delete_record":
        person = _get_person_or_error(ctx, tool_input["person_id"])
        if not tool_input.get("confirmed"):
            return {
                "status": "confirmation_required",
                "message": f"{person.name}さんのデータを削除（論理削除）します。よろしいですか？「削除する」「中止する」でお答えください。",
            }
        updated = person_service.soft_delete_confirmed(
            ctx.repo, ctx.db, ctx.line_user_id, person, tool_input.get("raw_input_text", "")
        )
        return {"status": "deleted", "deletion_status": updated.retention.deletion_status.value}

    if name in ("compare_people", "analyze_team"):
        return {
            "status": "not_implemented_phase2",
            "message": "この機能は第2段階で実装予定です（docs/phase2-design.md参照）。現在はご利用いただけません。",
        }

    if name == "prepare_person_update":
        person = _get_person_or_error(ctx, tool_input["person_id"])
        changes = tool_input["changes"]
        previews = [
            person_service.prepare_basic_info_update(ctx.repo, person, field_name, str(value))
            for field_name, value in changes.items()
        ]
        return {"status": "confirmation_required", "previews": previews}

    if name == "confirm_person_update":
        return {"status": "not_supported_via_tool", "message": "この経路は現行実装では未使用です（LINE会話状態経由の確認フローを使用してください）。"}

    raise ToolValidationError(f"未知のツールです: {name}")
