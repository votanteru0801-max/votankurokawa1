"""LINE Webhookエンドポイント。
署名検証・許可ユーザー照合・イベント重複防止をここで一元的に行い、
実処理（命式計算・AI呼び出し）はバックグラウンドタスクへ回して速やかに200を返す。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Header, Request, Response

from app.auth.line_auth import UNAUTHORIZED_MESSAGE, is_allowed_user, verify_signature
from app.config import get_settings
from app.db.base import get_engine
from app.db.models import WebhookEvent
from sqlalchemy.orm import Session

router = APIRouter()


def _reply_or_log(line_user_id: str, texts: list[str]) -> None:
    """LINEへ返信する。LINE_MODE=mockの場合はログのみ（テスト・ローカル用）。"""
    settings = get_settings()
    if settings.line_mode.value != "live":
        for t in texts:
            print(f"[MOCK LINE REPLY -> {line_user_id}] {t}")
        return
    from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, PushMessageRequest, TextMessage

    configuration = Configuration(access_token=settings.line_channel_access_token)
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        api.push_message(
            PushMessageRequest(to=line_user_id, messages=[TextMessage(text=t) for t in texts])
        )


def process_event(event: dict) -> None:
    """1件のWebhookイベントを処理する（バックグラウンドタスクから呼ばれる）。"""
    from app.ai.factory import get_ai_client
    from app.ai.orchestrator import Orchestrator
    from app.sheets.google_repository import get_person_repository

    settings = get_settings()
    engine = get_engine()
    with Session(engine) as db:
        webhook_event_id = event.get("webhookEventId") or str(uuid.uuid4())
        line_user_id = event.get("source", {}).get("userId", "")

        db_event = db.query(WebhookEvent).filter_by(line_event_id=webhook_event_id).one_or_none()
        if db_event is None:
            db_event = WebhookEvent(
                id=uuid.uuid4(),
                line_event_id=webhook_event_id,
                line_user_id=line_user_id,
                event_type=event.get("type", "unknown"),
                raw_payload=event,
                received_at=datetime.utcnow(),
                status="processing",
            )
            db.add(db_event)
            db.commit()
        elif db_event.status == "done":
            return  # 二重処理防止

        try:
            if not is_allowed_user(line_user_id):
                _reply_or_log(line_user_id, [UNAUTHORIZED_MESSAGE])
                db_event.status = "done"
                db_event.processed_at = datetime.utcnow()
                db.add(db_event)
                db.commit()
                return

            if event.get("type") != "message" or event.get("message", {}).get("type") != "text":
                db_event.status = "done"
                db_event.processed_at = datetime.utcnow()
                db.add(db_event)
                db.commit()
                return

            text = event["message"]["text"]
            repo = get_person_repository()
            ai_client = get_ai_client()
            orchestrator = Orchestrator(db, repo, ai_client)
            reply_texts = orchestrator.handle_message(line_user_id, text, webhook_event_id)
            _reply_or_log(line_user_id, reply_texts)

            db_event.status = "done"
            db_event.processed_at = datetime.utcnow()
            db.add(db_event)
            db.commit()
        except Exception as e:  # noqa: BLE001 内部エラーはユーザーに詳細を見せない
            from app.services.audit_service import log_error

            # 直前の例外でセッションが「ロールバック待ち」状態になっている場合があるため、
            # エラー記録の前に必ずロールバックしてセッションを使える状態に戻す。
            db.rollback()
            log_error(db, component="webhook", error_type=type(e).__name__, message=str(e), line_user_id=line_user_id)
            db_event.status = "error"
            db_event.error_message = str(e)
            db.add(db_event)
            db.commit()
            _reply_or_log(
                line_user_id,
                ["処理中にエラーが発生しました。時間をおいて再度お試しください。"],
            )


@router.post("/webhook")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: str = Header(default=""),
) -> Response:
    settings = get_settings()
    body = await request.body()

    if settings.line_mode.value == "live":
        if not verify_signature(body, x_line_signature, settings.line_channel_secret):
            return Response(status_code=403, content="invalid signature")

    payload = json.loads(body or b"{}")
    for event in payload.get("events", []):
        background_tasks.add_task(process_event, event)

    return Response(status_code=200, content="ok")
