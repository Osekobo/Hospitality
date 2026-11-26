import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from services.ai_agent import get_or_create_user, process_message
from services.meta_service import meta_service, parse_instagram_events, parse_whatsapp_events, verify_signature

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(tags=["meta webhooks"])


def verify_webhook(request: Request) -> PlainTextResponse:
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")
    if mode == "subscribe" and token == settings.meta_verify_token:
        return PlainTextResponse(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.get("/webhooks/meta")
@router.get("/webhooks/whatsapp")
@router.get("/webhooks/instagram")
async def meta_verify(request: Request) -> PlainTextResponse:
    return verify_webhook(request)


async def _handle_meta_post(request: Request, db: Session) -> dict[str, Any]:
    raw = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")
    if not verify_signature(raw, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if body.get("object") == "whatsapp_business_account":
        events = parse_whatsapp_events(body)
    elif body.get("object") == "instagram":
        events = parse_instagram_events(body)
    else:
        events = []

    processed = 0
    for event in events:
        try:
            user = get_or_create_user(
                db,
                platform=event["platform"],
                identifier=event["identifier"],
                name=event.get("name"),
            )
            result = await process_message(
                db,
                user,
                event["text"],
                event["platform"],
                external_id=event.get("message_id") or None,
            )
            if result.get("intent") == "duplicate":
                continue
            await meta_service.send_text(event["platform"], event["identifier"], result["reply"])
            processed += 1
        except Exception as exc:
            logger.exception("Failed to process Meta %s event: %s", event.get("platform"), exc)

    return {"status": "ok", "processed": processed}


@router.post("/webhooks/meta")
@router.post("/webhooks/whatsapp")
@router.post("/webhooks/instagram")
async def meta_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    return await _handle_meta_post(request, db)
