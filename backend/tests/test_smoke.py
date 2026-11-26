import hashlib
import hmac
import json
import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.mkdtemp(prefix='hospitality-test-'), 'test.db')}"
os.environ["DEMO_MODE"] = "true"
os.environ["META_APP_SECRET"] = "test-meta-secret"
os.environ["META_VERIFY_TOKEN"] = "test-verify-token"
os.environ["ADMIN_API_TOKEN"] = ""
os.environ["REWARD_AIRTIME_AMOUNT"] = "0"
os.environ["MPESA_CONSUMER_KEY"] = ""
os.environ["MPESA_CONSUMER_SECRET"] = ""
os.environ["MPESA_PASSKEY"] = ""
os.environ["AT_API_KEY"] = ""
os.environ["WHATSAPP_ACCESS_TOKEN"] = ""
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = ""
os.environ["INSTAGRAM_ACCESS_TOKEN"] = ""
os.environ["AI_PROVIDER"] = "none"
os.environ["GOOGLE_PLACES_API_KEY"] = ""
os.environ["OPENWEATHER_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

import database
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_root_and_health(client) -> None:
    assert client.get("/").status_code == 200
    health = client.get("/health").json()
    assert health == {"status": "ok", "database": "ok"}


def test_admin_endpoints(client) -> None:
    stats = client.get("/admin/stats").json()
    assert stats["total_users"] >= 4
    assert stats["total_revenue"] > 0
    assert len(stats["revenue_by_day"]) == 7
    assert len(client.get("/admin/bookings").json()) >= 6
    assert len(client.get("/admin/chats").json()) >= 8
    assert len(client.get("/admin/properties").json()) >= 5
    assert len(client.get("/mpesa/transactions").json()) >= 4


def test_chat_booking_creates_pending_payment(client) -> None:
    response = client.post(
        "/chat/message",
        json={"phone_number": "0799000123", "platform": "WA", "message": "I want to book a room tomorrow for 2 nights"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "booking"
    assert data["booking_id"] is not None
    assert data["checkout_request_id"].startswith("SIM_")


def test_admin_reply_does_not_create_booking(client) -> None:
    before = len(client.get("/admin/bookings").json())
    response = client.post(
        "/admin/chats/1/reply",
        json={"message": "Thank you for reaching out."},
    )
    assert response.status_code == 200
    assert response.json()["direction"] == "out"
    assert len(client.get("/admin/bookings").json()) == before


def test_mpesa_callback_marks_booking_paid(client) -> None:
    booking_id = client.post(
        "/chat/message",
        json={"phone_number": "0799000456", "platform": "IG", "message": "Reserve a room for next week, 2 guests"},
    ).json()["booking_id"]
    transaction = next(
        transaction for transaction in client.get("/mpesa/transactions").json() if transaction["booking_id"] == booking_id
    )
    callback = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "test-merchant",
                "CheckoutRequestID": transaction["checkout_request_id"],
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": transaction["amount"]},
                        {"Name": "MpesaReceiptNumber", "Value": "TEST123ABCD"},
                        {"Name": "PhoneNumber", "Value": 254799000456},
                    ]
                },
            }
        }
    }
    response = client.post("/mpesa/callback", json=callback)
    assert response.status_code == 200
    booking = next(booking for booking in client.get("/admin/bookings").json() if booking["id"] == booking_id)
    assert booking["status"] == "Paid"


def test_meta_and_ussd_webhooks(client) -> None:
    verify = client.get(
        "/webhooks/meta",
        params={"hub.mode": "subscribe", "hub.verify_token": "test-verify-token", "hub.challenge": "abc123"},
    )
    assert verify.status_code == 200
    assert verify.text == "abc123"

    wa_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "254700000000", "phone_number_id": "123"},
                            "contacts": [{"wa_id": "254700000001", "profile": {"name": "Test Guest"}}],
                            "messages": [
                                {"from": "254700000001", "id": "wamid.1", "type": "text", "text": {"body": "Habari!"}}
                            ],
                        },
                    }
                ],
            }
        ],
    }
    body = json.dumps(wa_payload).encode()
    signature = "sha256=" + hmac.new(b"test-meta-secret", body, hashlib.sha256).hexdigest()
    assert client.post(
        "/webhooks/meta",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature},
    ).json()["processed"] == 1

    ussd = client.post(
        "/webhooks/at/ussd",
        data={"sessionId": "s1", "serviceCode": "*389#", "phoneNumber": "254712345678", "text": ""},
    )
    assert ussd.status_code == 200
    assert ussd.text.startswith("CON")


def test_meta_signature_is_required(client) -> None:
    response = client.post("/webhooks/meta", json={"object": "unknown"})
    assert response.status_code == 401


def test_migration_adds_missing_columns(tmp_path, monkeypatch) -> None:
    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    phone_number VARCHAR(40),
                    platform VARCHAR(10),
                    display_name VARCHAR(120),
                    preferred_language VARCHAR(5),
                    created_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE chat_messages (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    platform VARCHAR(10),
                    direction VARCHAR(4),
                    content TEXT,
                    intent VARCHAR(40),
                    created_at DATETIME
                )
                """
            )
        )

    monkeypatch.setattr(database, "engine", legacy_engine)
    database.migrate_db()

    user_columns = {column["name"] for column in inspect(legacy_engine).get_columns("users")}
    chat_columns = {column["name"] for column in inspect(legacy_engine).get_columns("chat_messages")}
    assert "reward_granted" in user_columns
    assert "external_id" in chat_columns
