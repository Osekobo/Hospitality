import hmac
import os

from fastapi import Header, HTTPException

from config import get_settings


async def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    expected = settings.admin_api_token
    if not expected:
        return
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="Administrator token required or invalid")


def ensure_production_config() -> None:
    settings = get_settings()
    if settings.environment.strip().lower() in {"production", "prod", "staging"}:
        missing = []
        if not settings.admin_api_token:
            missing.append("ADMIN_API_TOKEN")
        if not settings.meta_app_secret:
            missing.append("META_APP_SECRET")
        if missing:
            raise RuntimeError("Missing required production settings: " + ", ".join(missing))


def configured_in_testing() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ
