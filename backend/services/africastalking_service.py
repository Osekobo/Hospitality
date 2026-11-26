from typing import Any

import httpx

from config import get_settings
from services.phone import normalize_phone

settings = get_settings()


class AfricaTalkingService:
    def __init__(self) -> None:
        base = "api.sandbox.africastalking.com" if settings.at_sandbox else "api.africastalking.com"
        self.base_url = f"https://{base}/version1"
        self.headers = {
            "apiKey": settings.at_api_key,
            "Accept": "application/json",
        }

    @property
    def configured(self) -> bool:
        return bool(settings.at_api_key)

    async def send_sms(self, to: str, message: str, sender_id: str | None = None) -> dict[str, Any]:
        if not self.configured:
            return {"status": "simulated", "to": normalize_phone(to), "message": message}

        payload = {
            "username": settings.at_username,
            "to": normalize_phone(to),
            "message": message,
        }
        sender = sender_id or settings.at_sender_id
        if sender:
            payload["from"] = sender

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/messaging",
                headers={**self.headers, "Content-Type": "application/x-www-form-urlencoded"},
                data=payload,
            )
            response.raise_for_status()
            return response.json()

    async def send_airtime(
        self, phone_number: str, amount_kes: float, metadata: dict[str, str] | None = None
    ) -> dict[str, Any]:
        if not self.configured:
            return {"status": "simulated", "phoneNumber": normalize_phone(phone_number), "amount": f"KES {amount_kes:.2f}"}

        payload: dict[str, Any] = {
            "username": settings.at_username,
            "recipients": [
                {"phoneNumber": normalize_phone(phone_number), "amount": f"KES {amount_kes:.2f}"}
            ],
        }
        if metadata:
            payload["requestMetadata"] = {k: str(v) for k, v in metadata.items()}

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/airtime/send",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def send_ussd_prompt(self, phone_number: str, text: str) -> dict[str, Any]:
        if not self.configured:
            return {"status": "simulated", "phoneNumber": normalize_phone(phone_number), "text": text}

        payload = {
            "username": settings.at_username,
            "phoneNumber": normalize_phone(phone_number),
            "serviceCode": settings.at_ussd_service_code,
            "text": text,
            "responseType": "irreversible",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/ussd/initiate",
                headers={**self.headers, "Content-Type": "application/x-www-form-urlencoded"},
                data=payload,
            )
            response.raise_for_status()
            return response.json()


africastalking_service = AfricaTalkingService()
