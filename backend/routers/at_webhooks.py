import hmac
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import Booking, Property, Transaction, User
from services.africastalking_service import africastalking_service
from services.ai_agent import get_or_create_user, process_message
from services.mpesa_service import mpesa_service
from services.phone import normalize_phone

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(tags=["Africa's Talking webhooks"])


def _verify_webhook_token(token: str | None) -> None:
    expected = settings.at_webhook_secret
    if expected and (not token or not hmac.compare_digest(token, expected)):
        raise HTTPException(status_code=401, detail="Invalid webhook token")


def _parse_ussd_date(value: str) -> date | None:
    for pattern in ("%d%m%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _booking_menu(db: Session) -> str:
    properties = db.query(Property).order_by(Property.rating.desc()).limit(4).all()
    lines = "\n".join(
        f"{index}. {property.name} - KES {property.price_per_night:,.0f}"
        for index, property in enumerate(properties, start=1)
    )
    return f"CON Book a stay:\n{lines}\n0. Back"


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


async def customer_ussd(phone: str, text: str, db: Session) -> PlainTextResponse:
    parts = [part for part in text.split("*") if part]

    if not parts:
        return PlainTextResponse(
            "CON Social Concierge\n1. My bookings\n2. Book a stay\n3. Help\n0. Exit"
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
        if len(parts) == 1:
            return PlainTextResponse(_booking_menu(db))
        if parts[1] == "0":
            return PlainTextResponse("CON Social Concierge\n1. My bookings\n2. Book a stay\n3. Help\n0. Exit")
        if not parts[1].isdigit():
            return PlainTextResponse("END Invalid property. Dial *389# to try again.")
        property_index = int(parts[1]) - 1
        if property_index < 0 or property_index >= len(properties):
            return PlainTextResponse("END Invalid property. Dial *389# to try again.")
        property_obj = properties[property_index]

        if len(parts) == 2:
            return PlainTextResponse(
                f"CON {property_obj.name} - KES {property_obj.price_per_night:,.0f}/night\n"
                "Enter check-in date DDMMYYYY\n0. Back"
            )
        if parts[2] == "0":
            return PlainTextResponse(_booking_menu(db))
        check_in = _parse_ussd_date(parts[2])
        if check_in is None or check_in < date.today():
            return PlainTextResponse("END Invalid check-in date. Use DDMMYYYY.")

        if len(parts) == 3:
            return PlainTextResponse("CON Enter check-out date DDMMYYYY\n0. Back")
        if parts[3] == "0":
            return PlainTextResponse(_booking_menu(db))
        check_out = _parse_ussd_date(parts[3])
        if check_out is None or check_out <= check_in:
            return PlainTextResponse("END Check-out must be after check-in. Use DDMMYYYY.")

        if len(parts) == 4:
            return PlainTextResponse("CON Enter number of guests (1-20)\n0. Back")
        if parts[4] == "0":
            return PlainTextResponse(_booking_menu(db))
        if not parts[4].isdigit():
            return PlainTextResponse("END Invalid number of guests.")
        guests = int(parts[4])
        if not 1 <= guests <= 20:
            return PlainTextResponse("END Guests must be between 1 and 20.")

        nights = (check_out - check_in).days
        total = float(property_obj.price_per_night) * nights
        deposit = round(total * 0.5)
        if len(parts) == 5:
            return PlainTextResponse(
                f"CON {property_obj.name}\n{check_in.isoformat()} to {check_out.isoformat()} - {guests} guests\n"
                f"Total KES {total:,.0f}. Deposit KES {deposit:,.0f}\n"
                "1. Confirm and pay\n2. Choose another property\n0. Cancel"
            )
        if parts[5] == "2":
            return PlainTextResponse(_booking_menu(db))
        if parts[5] == "0":
            return PlainTextResponse("END Booking cancelled.")
        if parts[5] != "1":
            return PlainTextResponse("END Invalid option. Dial *389# to try again.")

        user = get_or_create_user(db, "USSD", phone)
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
        try:
            payment = await mpesa_service.stk_push(
                user.phone_number, deposit, f"USSD{booking.id}", "Booking deposit"
            )
            if str(payment.get("ResponseCode")) != "0":
                db.commit()
                return PlainTextResponse(
                    f"END Booking {booking.id} saved, but M-Pesa rejected the prompt. Please try again."
                )
        except Exception as exc:
            logger.exception("USSD M-Pesa STK push failed for booking %s", booking.id)
            db.commit()
            return PlainTextResponse(
                f"END Booking {booking.id} saved, but the M-Pesa prompt failed. Please try again later."
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
        return PlainTextResponse(
            f"END Booking {booking.id} confirmed. Complete the M-Pesa prompt for KES {deposit:,.0f} to pay."
        )

    if option == "3":
        return PlainTextResponse("END Use option 2 to book and pay. Use option 1 to check your bookings.")

    if option == "0":
        return PlainTextResponse("END Thank you for using Social Concierge.")

    return PlainTextResponse("END Invalid option. Dial *389# to try again.")


@router.post("/webhooks/at/ussd")
@router.get("/webhooks/at/ussd", response_class=PlainTextResponse)
async def at_ussd_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_token: str | None = Header(default=None),
) -> PlainTextResponse:
    _verify_webhook_token(x_webhook_token)
    if request.method == "GET":
        return PlainTextResponse("CON Social Concierge\n1. My bookings\n2. Book a stay\n3. Help\n0. Exit")
    form = await request.form()
    phone = str(form.get("phoneNumber") or "")
    text = str(form.get("text") or "").strip()
    return await customer_ussd(phone, text, db)


@router.post("/ussd", response_class=PlainTextResponse)
async def customer_ussd_webhook(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_db),
    x_webhook_token: str | None = Header(default=None),
) -> PlainTextResponse:
    _verify_webhook_token(x_webhook_token)
    return await customer_ussd(phoneNumber, text.strip(), db)


def _find_guide(db: Session, phone_number: str) -> User | None:
    return db.query(User).filter(User.phone_number == normalize_phone(phone_number)).first()


@router.post("/guide/ussd", response_class=PlainTextResponse)
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
