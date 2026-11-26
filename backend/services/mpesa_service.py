import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from config import get_settings
from services.phone import normalize_phone

settings = get_settings()
logger = logging.getLogger(__name__)


def eat_timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=3))).strftime("%Y%m%d%H%M%S")


class MpesaService:
    def __init__(self) -> None:
        self.base_url = "https://sandbox.safaricom.co.ke" if settings.mpesa_sandbox else "https://api.safaricom.co.ke"
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    @property
    def configured(self) -> bool:
        return bool(settings.mpesa_consumer_key and settings.mpesa_consumer_secret and settings.mpesa_passkey)

    async def get_access_token(self) -> str:
        if self._token and self._token_expires_at and datetime.now() < self._token_expires_at:
            return self._token

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}/oauth/v1/generate",
                params={"grant_type": "client_credentials"},
                auth=(settings.mpesa_consumer_key, settings.mpesa_consumer_secret),
            )
            response.raise_for_status()
            data = response.json()

        self._token = data["access_token"]
        self._token_expires_at = datetime.now() + timedelta(seconds=int(data.get("expires_in", 3599)) - 60)
        return self._token

    async def stk_push(
        self, phone_number: str, amount: float, account_reference: str, transaction_desc: str = "Booking deposit"
    ) -> dict[str, Any]:
        phone = normalize_phone(phone_number, style="msisdn")
        amount = float(round(amount))

        if not self.configured:
            checkout_request_id = f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            return {
                "status": "simulated",
                "MerchantRequestID": f"SIM_MERCHANT_{checkout_request_id}",
                "CheckoutRequestID": checkout_request_id,
                "ResponseCode": "0",
                "ResponseDescription": "Success. Request accepted for processing (simulated)",
                "CustomerMessage": "Success. Request accepted for processing (simulated)",
            }

        token = await self.get_access_token()
        timestamp = eat_timestamp()
        password = base64.b64encode(
            f"{settings.mpesa_shortcode}{settings.mpesa_passkey}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": settings.mpesa_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": settings.mpesa_transaction_type,
            "Amount": amount,
            "PartyA": phone,
            "PartyB": settings.mpesa_shortcode,
            "PhoneNumber": phone,
            "CallBackURL": settings.mpesa_callback_url,
            "AccountReference": account_reference[:12],
            "TransactionDesc": transaction_desc[:13],
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
            if response.status_code >= 400:
                logger.error("M-Pesa STK failed with HTTP %s: %s", response.status_code, response.text[:500])
            response.raise_for_status()
            return response.json()

    async def query_status(self, checkout_request_id: str) -> dict[str, Any]:
        if not self.configured:
            return {"status": "simulated", "CheckoutRequestID": checkout_request_id, "ResultCode": "0"}

        token = await self.get_access_token()
        timestamp = eat_timestamp()
        password = base64.b64encode(
            f"{settings.mpesa_shortcode}{settings.mpesa_passkey}{timestamp}".encode()
        ).decode()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "BusinessShortCode": settings.mpesa_shortcode,
                    "Password": password,
                    "Timestamp": timestamp,
                    "CheckoutRequestID": checkout_request_id,
                },
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def parse_callback(body: dict[str, Any]) -> dict[str, Any]:
        callback = body.get("Body", {}).get("stkCallback", {})
        items = callback.get("CallbackMetadata", {}).get("Item", [])
        metadata = {item.get("Name"): item.get("Value") for item in items}
        result_code = callback.get("ResultCode")
        success = str(result_code) == "0"
        return {
            "merchant_request_id": callback.get("MerchantRequestID"),
            "checkout_request_id": callback.get("CheckoutRequestID"),
            "result_code": result_code,
            "result_description": callback.get("ResultDesc"),
            "success": success,
            "receipt": metadata.get("MpesaReceiptNumber"),
            "amount": metadata.get("Amount"),
            "phone": metadata.get("PhoneNumber"),
            "transaction_date": metadata.get("TransactionDate"),
        }


mpesa_service = MpesaService()
