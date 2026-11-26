import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import get_settings
from database import SessionLocal, get_db, init_db
from routers import admin, at_webhooks, chat, meta_webhooks, mpesa
from routers.at_webhooks import guide_ussd
from security import ensure_production_config, require_admin

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    ensure_production_config()
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)

app.include_router(meta_webhooks.router)
app.include_router(at_webhooks.router)
app.include_router(mpesa.router)
app.include_router(admin.router, dependencies=[Depends(require_admin)])
app.include_router(chat.router)


@app.get("/")
async def root() -> dict[str, object]:
    return {
        "name": settings.app_name,
        "status": "running",
        "docs": "/docs",
        "demo_mode": settings.demo_mode,
    }


@app.post("/", response_class=PlainTextResponse)
async def root_ussd(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    return await guide_ussd(
        sessionId=sessionId,
        serviceCode=serviceCode,
        phoneNumber=phoneNumber,
        text=text,
        db=db,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        database_status = "unavailable"
    finally:
        db.close()
    return {"status": "ok" if database_status == "ok" else "degraded", "database": database_status}
