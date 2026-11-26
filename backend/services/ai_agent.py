import json
import re
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from config import get_settings
from database import SessionLocal
from models import Booking, ChatMessage, Property, Transaction, User
from services.africastalking_service import africastalking_service
from services.phone import normalize_phone
from services.mpesa_service import mpesa_service
from services.places_weather import current_weather, safety_note, search_places

settings = get_settings()
SESSIONS: dict[str, list[dict[str, str]]] = {}

SYSTEM_PROMPT = """You are The Social Concierge, a warm AI travel assistant for African hospitality and tourism.
You chat on WhatsApp, Instagram DMs, SMS and USSD. You help travelers discover destinations, book stays,
pay deposits through M-Pesa, and stay safe with weather/advisory information.

Always answer with a single valid JSON object and no markdown, using these keys:
{
  "reply": "the message shown to the traveler (max 500 chars)",
  "language": "en or sw",
  "intent": "booking | recommendation | safety | faq | greeting | other",
  "property_query": "name or location of the property the traveler wants, else empty string",
  "check_in": "YYYY-MM-DD or empty string",
  "check_out": "YYYY-MM-DD or empty string",
  "guests": 2
}
Detect Swahili and reply in Swahili when the traveler writes in Swahili.
Never invent prices or confirmations. If a booking is requested, keep the reply short and say an M-Pesa prompt is being sent.
"""


def get_or_create_user(
    db: Session, platform: str, identifier: str, name: str | None = None, language: str | None = None
) -> User:
    phone_number = normalize_phone(identifier)
    user = db.query(User).filter(User.platform == platform, User.phone_number == phone_number).first()
    if user is None:
        user = User(
            phone_number=phone_number,
            platform=platform,
            display_name=name or "Traveler",
            preferred_language=language or "en",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def _rule_intent(text: str) -> str:
    value = text.lower()
    if any(word in value for word in ["book", "reserve", "room", "nafasi", "weka", "kulala", "stay", "deposit"]):
        return "booking"
    if any(word in value for word in ["recommend", "places", "near", "attraction", "wapi", "mahali", "things to do", "best"]):
        return "recommendation"
    if any(word in value for word in ["weather", "rain", "safe", "alert", "mvua", "hatari", "road", "closure"]):
        return "safety"
    if any(word in value for word in ["price", "how much", "cost", "gharama", "bei", "deposit"]):
        return "faq"
    if any(word in value for word in ["hi", "hello", "habari", "jambo", "hey", "start"]):
        return "greeting"
    return "other"


def _parse_date(value: str | None, fallback: date) -> date | None:
    if not value:
        return None
    cleaned = str(value).strip().lower()
    today = date.today()
    if cleaned in {"today", "leo"}:
        return today
    if cleaned in {"tomorrow", "kesho"}:
        return today + timedelta(days=1)
    if cleaned in {"next week", "wiki ijayo"}:
        return today + timedelta(days=7)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%B %d %Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    match = re.search(r"(\d{1,2})\s*(?:st|nd|rd|th)?\s*([a-z]+)", cleaned)
    if match:
        try:
            return datetime.strptime(f"{match.group(1)} {match.group(2)} {today.year}", "%d %B %Y").date()
        except ValueError:
            return None
    return None


def _extract_json(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).rstrip("`").strip()
    try:
        result = json.loads(cleaned)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start == -1:
            return None
        try:
            result, _ = json.JSONDecoder().raw_decode(cleaned[start:])
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            return None


async def _ask_llm(history: list[dict[str, str]], context: str) -> dict[str, Any] | None:
    if not settings.ai_enabled:
        return None

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            if settings.ai_provider == "openai":
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.openai_model,
                        "temperature": 0.3,
                        "response_format": {"type": "json_object"},
                        "messages": [{"role": "system", "content": SYSTEM_PROMPT + "\n\nContext:\n" + context}] + history[-8:],
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            elif settings.ai_provider == "gemini":
                conversation = "\n".join(f"{item['role']}: {item['content']}" for item in history[-8:])
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
                    params={"key": settings.gemini_api_key},
                    json={
                        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT + "\n\nContext:\n" + context}]},
                        "contents": [{"role": "user", "parts": [{"text": conversation}]}],
                        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
                    },
                )
                response.raise_for_status()
                content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return None
        return _extract_json(content)
    except Exception:
        return None


def _swahili_reply(intent: str, property_name: str, check_in: str, check_out: str, deposit: float, extra: str) -> str:
    templates = {
        "booking": (
            f"Nimekupatia {property_name} kwa tarehe {check_in} hadi {check_out}. "
            f"Tuma KES {deposit:,.0f} kupitia M-Pesa ili kuthibitisha nafasi yako."
        ),
        "recommendation": f"Hapa kuna mahali pazuri: {extra}. Niwatumie maelezo zaidi?",
        "safety": f"Habari za hali ya hewa: {extra}. Safiri salama!",
        "faq": "Ninaweza kukusaidia bei, nafasi na malipo. Unataka ku-book?",
        "greeting": "Jambo! Karibu. Nakuongoza kwenye hoteli, nafasi na malipo ya M-Pesa.",
    }
    return templates.get(intent, "Samahani, sijaelewa vizuri. Unaweza kuandika tena?")


def _english_reply(intent: str, property_name: str, check_in: str, check_out: str, deposit: float, extra: str) -> str:
    templates = {
        "booking": (
            f"I found {property_name} for {check_in} to {check_out}. "
            f"An M-Pesa prompt for KES {deposit:,.0f} is on its way to confirm your stay."
        ),
        "recommendation": f"Here are some great options: {extra}. Want me to book one?",
        "safety": f"Weather update: {extra}. Travel safely!",
        "faq": "I can help with prices, availability and payments. Would you like to book?",
        "greeting": "Hi! I'm your travel concierge — I can find stays, book them and take M-Pesa deposits.",
    }
    return templates.get(intent, "Sorry, I didn't quite catch that. Could you rephrase?")


async def process_message(
    db: Session,
    user: User,
    text: str,
    platform: str | None = None,
    external_id: str | None = None,
) -> dict[str, Any]:
    platform = platform or user.platform
    if external_id and db.query(ChatMessage.id).filter(ChatMessage.external_id == external_id).first():
        return {"intent": "duplicate", "language": user.preferred_language, "booking_id": None, "checkout_request_id": None, "reply": ""}
    if external_id:
        db.add(
            ChatMessage(
                user_id=user.id,
                platform=platform,
                direction="in",
                content=text,
                intent="pending",
                external_id=external_id,
            )
        )
        db.commit()

    session_key = f"{platform}:{user.phone_number}"
    history = SESSIONS.setdefault(session_key, [])
    history.append({"role": "user", "content": text})
    history[:] = history[-12:]

    rule_intent = _rule_intent(text)
    weather = await current_weather()
    places: list[dict[str, Any]] = []

    properties = db.query(Property).order_by(Property.rating.desc()).limit(10).all()
    property_lines = "\n".join(
        f"- {p.name} ({p.location}) | KES {p.price_per_night:,.0f}/night | rating {p.rating}" for p in properties
    )
    context = f"Available properties:\n{property_lines}\nWeather: {weather['description']} {weather['temperature']}C in {weather['city']}."

    if rule_intent in {"recommendation", "booking", "safety"}:
        places = await search_places(text, settings.default_city)
        context += "\nNearby places: " + ", ".join(p["name"] for p in places)

    parsed = await _ask_llm(history, context) or {}
    intent = str(parsed.get("intent") or rule_intent).lower()
    if intent not in {"booking", "recommendation", "safety", "faq", "greeting", "other"}:
        intent = rule_intent

    language = str(parsed.get("language") or user.preferred_language or "en").lower()
    if language not in {"en", "sw"}:
        language = "en"

    result: dict[str, Any] = {"intent": intent, "language": language, "booking_id": None, "checkout_request_id": None}

    if intent == "booking":
        query = str(parsed.get("property_query") or "").lower()
        match = next(
            (p for p in properties if query and (query in p.name.lower() or query in p.location.lower())),
            None,
        )
        property_obj = (match or properties[0]) if properties else None
        deposit = 0.0
        checkout_request_id = ""
        result.update(
            {
                "check_in": (date.today() + timedelta(days=1)).isoformat(),
                "check_out": (date.today() + timedelta(days=3)).isoformat(),
            }
        )

        today = date.today()
        check_in = _parse_date(parsed.get("check_in"), today) or today + timedelta(days=1)
        if check_in < today:
            check_in = today
        check_out = _parse_date(parsed.get("check_out"), check_in + timedelta(days=2)) or check_in + timedelta(days=2)
        if check_out <= check_in:
            check_out = check_in + timedelta(days=1)
        try:
            guests = int(parsed.get("guests") or 2)
        except (TypeError, ValueError):
            guests = 2
        guests = min(max(guests, 1), 20)

        if property_obj:
            nights = (check_out - check_in).days
            total = float(property_obj.price_per_night) * nights
            deposit = round(total * 0.5)
            booking = Booking(
                user_id=user.id,
                property_id=property_obj.id,
                check_in=check_in.isoformat(),
                check_out=check_out.isoformat(),
                guests=guests,
                status="Pending",
                total_amount=total,
            )
            db.add(booking)
            db.flush()

            payment = await mpesa_service.stk_push(
                user.phone_number, deposit, f"BK{booking.id}", "Booking deposit"
            )
            checkout_request_id = str(payment.get("CheckoutRequestID", ""))
            booking.mpesa_checkout_request_id = checkout_request_id
            db.add(
                Transaction(
                    booking_id=booking.id,
                    checkout_request_id=checkout_request_id,
                    merchant_request_id=payment.get("MerchantRequestID"),
                    amount=deposit,
                    status="Pending",
                    phone_number=user.phone_number,
                    result_description=payment.get("ResponseDescription"),
                )
            )
            db.commit()

            result.update(
                {
                    "booking_id": booking.id,
                    "checkout_request_id": checkout_request_id,
                    "property": property_obj.name,
                    "check_in": check_in.isoformat(),
                    "check_out": check_out.isoformat(),
                    "deposit": deposit,
                }
            )
        else:
            deposit = 0.0
            property_name = "a stay"

        llm_reply = str(parsed.get("reply") or "").strip()
        if llm_reply:
            reply = llm_reply
        elif language == "sw":
            reply = _swahili_reply(intent, result.get("property", "hoteli"), result["check_in"], result["check_out"], deposit, "")
        else:
            reply = _english_reply(intent, result.get("property", "a stay"), result["check_in"], result["check_out"], deposit, "")
    else:
        place_summary = ", ".join(p["name"] for p in places[:3]) or "Pinetree Boutique Hotel, Maasai Oasis Camp"
        weather_extra = f"{weather['description']}, {weather['temperature']}C. {safety_note(weather)}"
        llm_reply = str(parsed.get("reply") or "").strip()
        if llm_reply:
            reply = llm_reply
        elif language == "sw":
            reply = _swahili_reply(intent, "", "", "", 0.0, place_summary if intent == "recommendation" else weather_extra)
        else:
            reply = _english_reply(intent, "", "", "", 0.0, place_summary if intent == "recommendation" else weather_extra)

    if not external_id:
        db.add(ChatMessage(user_id=user.id, platform=platform, direction="in", content=text, intent=intent))
    db.add(ChatMessage(user_id=user.id, platform=platform, direction="out", content=reply[:500], intent=intent))
    db.commit()

    history.append({"role": "assistant", "content": reply[:500]})
    history[:] = history[-12:]
    result["reply"] = reply[:500]
    return result


async def send_booking_confirmation(db: Session, booking: Booking) -> None:
    user = db.query(User).filter(User.id == booking.user_id).first()
    property_obj = db.query(Property).filter(Property.id == booking.property_id).first()
    if not user or not property_obj:
        return
    language = user.preferred_language
    message = (
        f"Karibu! Nafasi yako imethibitishwa: {property_obj.name}, {booking.check_in} - {booking.check_out}. Asante!"
        if language == "sw"
        else f"Confirmed! Your stay at {property_obj.name} ({booking.check_in} to {booking.check_out}) is paid. See you soon!"
    )
    await africastalking_service.send_sms(user.phone_number, message)
    db.add(ChatMessage(user_id=user.id, platform=user.platform, direction="out", content=message, intent="booking"))
    db.commit()


async def reward_loyal_guest(db: Session, user: User) -> None:
    amount = settings.reward_airtime_amount
    if amount <= 0:
        return
    await africastalking_service.send_airtime(
        user.phone_number, amount, {"reason": "repeat-guest-reward", "userId": str(user.id)}
    )
