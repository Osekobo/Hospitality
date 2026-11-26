from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import ChatRequest
from security import require_admin
from services.ai_agent import SESSIONS, get_or_create_user, process_message
from services.phone import normalize_phone

router = APIRouter(prefix="/chat", tags=["concierge chat"])


@router.post("/message", dependencies=[Depends(require_admin)])
async def send_chat_message(payload: ChatRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = get_or_create_user(
        db,
        platform=payload.platform.upper(),
        identifier=normalize_phone(payload.phone_number),
        name=payload.name,
        language=payload.language,
    )
    return await process_message(db, user, payload.message, payload.platform.upper())


@router.get("/sessions", dependencies=[Depends(require_admin)])
async def active_sessions() -> dict[str, Any]:
    return {
        "count": len(SESSIONS),
        "messages": sum(len(messages) for messages in SESSIONS.values()),
    }
