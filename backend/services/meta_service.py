import hashlib
import hmac
from typing import Any

import httpx

from config import get_settings

settings = get_settings()


def verify_signature(payload: bytes, signature: str) -> bool:
    if not settings.meta_app_secret or not signature:
        return False
    digest = hmac.new(settings.meta_app_secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={digest}", signature)


def parse_whatsapp_events(body: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if value.get("messaging_product") != "whatsapp":
                continue
            contacts = {c.get("wa_id"): c.get("profile", {}).get("name", "Traveler") for c in value.get("contacts", [])}
            for message in value.get("messages", []):
                if message.get("type") != "text" or not message.get("text", {}).get("body"):
                    continue
                sender = message.get("from") or message.get("from_user_id")
                if not sender:
                    continue
                events.append(
                    {
                        "platform": "WA",
                        "identifier": sender,
                        "name": contacts.get(sender, "Traveler"),
                        "text": message["text"]["body"],
                        "message_id": message.get("id", ""),
                        "timestamp": message.get("timestamp"),
                    }
                )
    return events


def parse_instagram_events(body: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            message = event.get("message", {})
            if message.get("is_echo") or not message.get("text"):
                continue
            sender = event.get("sender", {}).get("id")
            if not sender:
                continue
            events.append(
                {
                    "platform": "IG",
                    "identifier": sender,
                    "name": "Instagram Traveler",
                    "text": message["text"],
                    "message_id": message.get("mid", ""),
                    "timestamp": event.get("timestamp"),
                }
            )
    return events


class MetaService:
    @property
    def graph_url(self) -> str:
        return f"https://graph.facebook.com/{settings.meta_api_version}"

    async def send_whatsapp_text(self, to: str, text: str) -> dict[str, Any]:
        if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
            return {"status": "simulated", "channel": "whatsapp", "to": to, "text": text}

        url = f"{self.graph_url}/{settings.whatsapp_phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text[:4096]},
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.whatsapp_access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def send_instagram_text(self, recipient_id: str, text: str) -> dict[str, Any]:
        if not settings.instagram_access_token:
            return {"status": "simulated", "channel": "instagram", "to": recipient_id, "text": text}

        url = f"{self.graph_url}/{settings.instagram_page_id}/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text[:1000]},
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                params={"access_token": settings.instagram_access_token},
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def send_text(self, platform: str, recipient: str, text: str) -> dict[str, Any]:
        if platform == "IG":
            return await self.send_instagram_text(recipient, text)
        return await self.send_whatsapp_text(recipient, text)


meta_service = MetaService()
