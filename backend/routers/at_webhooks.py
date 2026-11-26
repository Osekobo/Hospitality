import hmac
from datetime import date

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import Booking, Property, User
from services.africastalking_service import africastalking_service
from services.ai_agent import get_or_create_user, process_message
from services.phone import normalize_phone

settings = get_settings()
router = APIRouter(tags=["Africa's Talking webhooks"])


def _verify_webhook_token(token: str | None) -> None:
    expected = settings.at_webhook_secret
    if expected and (not token or not hmac.compare_digest(token, expected)):
        raise HTTPException(status_code=401, detail="Invalid webhook token")


@router.post("/webhooks/at/sms")
async def at_sms_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_token: str | None = Header(default=None),
) -> dict[str, str]:
    _verify_webhook_token(x_webhook_token)
    form = await request.form()
    sender = str(form.get("from") or form.get("phoneNumber") or "")
    text = str(form.get("text") or form.get("message") or "")

    if sender and text:
        user = get_or_create_user(db, "SMS", sender)
        result = await process_message(db, user, text, "SMS")
        await africastalking_service.send_sms(user.phone_number, result["reply"])

    return {"status": "ok"}


@router.post("/webhooks/at/ussd")
@router.get("/webhooks/at/ussd", response_class=PlainTextResponse)
async def at_ussd_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_token: str | None = Header(default=None),
) -> PlainTextResponse:
    _verify_webhook_token(x_webhook_token)
    if request.method == "GET":
        return PlainTextResponse("CON Social Concierge\n1. My bookings\n2. Explore places\n3. Help\n0. Exit")

    form = await request.form()
    phone = str(form.get("phoneNumber") or "")
    text = str(form.get("text") or "").strip()
    parts = [part for part in text.split("*") if part]

    if not parts:
        return PlainTextResponse(
            "CON Social Concierge\n1. My bookings\n2. Explore places\n3. Help\n0. Exit"
        )

    option = parts[0]
    if option == "1":
        user = get_or_create_user(db, "USSD", phone)
        bookings = [booking for booking in user.bookings if booking.status != "Cancelled"]
        if not bookings:
            return PlainTextResponse("END You have no active bookings. Reply *389# to explore places.")
        lines = "\n".join(
            f"{index}. {booking.property.name} {booking.check_in} to {booking.check_out} - {booking.status}"
            for index, booking in enumerate(bookings, start=1)
        )
        return PlainTextResponse(f"CON Your bookings:\n{lines}\n0. Back")

    if option == "2":
        properties = db.query(Property).order_by(Property.rating.desc()).limit(4).all()
        lines = "\n".join(f"{index}. {p.name} - KES {p.price_per_night:,.0f}" for index, p in enumerate(properties, start=1))
        return PlainTextResponse(f"CON Explore places:\n{lines}\n0. Back")

    if option == "3":
        return PlainTextResponse("END Book by chatting on WhatsApp or Instagram, then use *389# to check status.")

    if option == "0":
        return PlainTextResponse("END Thank you for using Social Concierge.")

    return PlainTextResponse("END Invalid option. Dial *389# to try again.")


def _find_guide(db: Session, phone_number: str) -> User | None:
    return db.query(User).filter(User.phone_number == normalize_phone(phone_number)).first()


@router.post("/ussd", response_class=PlainTextResponse)
async def guide_ussd(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_db),
    x_webhook_token: str | None = Header(default=None),
) -> PlainTextResponse:
    _verify_webhook_token(x_webhook_token)
    option = text.strip()

    if not option:
        return PlainTextResponse(
            "CON Welcome to the Guide Portal\n1. View Today's Bookings\n2. My Profile"
        )

    if option == "1":
        guide = _find_guide(db, phoneNumber)
        if guide is None:
            return PlainTextResponse("END You have no bookings today.")

        today = date.today().isoformat()
        rows = (
            db.query(Booking, Property)
            .join(Property, Booking.property_id == Property.id)
            .filter(
                Booking.user_id == guide.id,
                Booking.check_in == today,
                Booking.status != "Cancelled",
            )
            .order_by(Booking.id)
            .all()
        )
        if not rows:
            return PlainTextResponse("END You have no bookings today.")

        next_booking, next_property = rows[0]
        return PlainTextResponse(
            f"END You have {len(rows)} bookings today. "
            f"Next: {next_property.name} at {next_booking.check_in}."
        )

    if option == "2":
        guide = _find_guide(db, phoneNumber)
        guide_name = guide.display_name if guide and guide.display_name else "Guide"
        return PlainTextResponse(f"END Name: {guide_name}\nStatus: Active")

    return PlainTextResponse("END Invalid option. Please try again.")
