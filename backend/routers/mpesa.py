import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import Booking, Transaction, User
from schemas import STKPushRequest
from security import require_admin
from services.africastalking_service import africastalking_service
from services.ai_agent import reward_loyal_guest, send_booking_confirmation
from services.phone import normalize_phone
from services.mpesa_service import mpesa_service
from utils import iso_utc

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/mpesa", tags=["M-Pesa Daraja"])


@router.post("/stk-push", dependencies=[Depends(require_admin)])
async def initiate_stk_push(payload: STKPushRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    booking = None
    if payload.booking_id:
        booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
        if booking is None:
            raise HTTPException(status_code=404, detail="Booking not found")

    amount = payload.amount or (booking.total_amount * 0.5 if booking else 1000.0)
    account_reference = payload.account_reference or (f"BK{booking.id}" if booking else "CONCIERGE")
    phone = normalize_phone(payload.phone_number, style="msisdn")
    response = await mpesa_service.stk_push(phone, amount, account_reference)

    if str(response.get("ResponseCode", "0")) != "0":
        raise HTTPException(
            status_code=502,
            detail=response.get("ResponseDescription") or "M-Pesa rejected the payment request",
        )

    checkout_request_id = str(response.get("CheckoutRequestID") or "")
    if not checkout_request_id:
        raise HTTPException(status_code=502, detail="M-Pesa did not return a checkout request ID")

    transaction = Transaction(
        booking_id=booking.id if booking else None,
        checkout_request_id=checkout_request_id,
        merchant_request_id=response.get("MerchantRequestID"),
        amount=round(float(amount), 2),
        status="Pending",
        phone_number=normalize_phone(phone),
        result_description=response.get("ResponseDescription"),
    )
    db.add(transaction)
    if booking:
        booking.mpesa_checkout_request_id = checkout_request_id
    db.commit()
    db.refresh(transaction)

    return {
        "transaction_id": transaction.id,
        "booking_id": booking.id if booking else None,
        "amount": transaction.amount,
        "phone_number": transaction.phone_number,
        "merchant_request_id": transaction.merchant_request_id,
        "checkout_request_id": transaction.checkout_request_id,
        "response_code": response.get("ResponseCode"),
        "customer_message": response.get("CustomerMessage"),
        "simulated": response.get("status") == "simulated",
    }


@router.post("/callback")
async def stk_callback(body: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    result = mpesa_service.parse_callback(body)
    checkout_request_id = result["checkout_request_id"]
    transaction = None
    if checkout_request_id:
        transaction = db.query(Transaction).filter(Transaction.checkout_request_id == checkout_request_id).first()

    if transaction is None:
        return {"ResultCode": 0, "ResultDesc": "Accepted (unknown checkout id)"}

    if transaction.status in {"Success", "Failed"}:
        return {"ResultCode": 0, "ResultDesc": "Accepted (already processed)"}

    transaction.result_description = result["result_description"]
    if result["success"]:
        callback_amount = result.get("amount")
        callback_phone = result.get("phone")
        if callback_amount and abs(float(callback_amount) - float(transaction.amount or 0)) > 1:
            logger.warning("M-Pesa amount mismatch for %s", checkout_request_id)
            transaction.status = "Failed"
            transaction.result_description = "Callback amount did not match the pending transaction"
            db.commit()
            return {"ResultCode": 0, "ResultDesc": "Accepted (amount mismatch)"}
        if callback_phone and normalize_phone(str(callback_phone), style="msisdn") != normalize_phone(
            transaction.phone_number or "", style="msisdn"
        ):
            logger.warning("M-Pesa phone mismatch for %s", checkout_request_id)
            transaction.status = "Failed"
            transaction.result_description = "Callback phone did not match the pending transaction"
            db.commit()
            return {"ResultCode": 0, "ResultDesc": "Accepted (phone mismatch)"}

        transaction.status = "Success"
        if result.get("receipt"):
            transaction.mpesa_receipt_number = str(result["receipt"])
        if callback_amount:
            transaction.amount = float(callback_amount)

        booking = db.query(Booking).filter(Booking.id == transaction.booking_id).first() if transaction.booking_id else None
        if booking:
            was_paid = booking.status == "Paid"
            booking.status = "Paid"
        db.commit()

        if booking and not was_paid:
            await send_booking_confirmation(db, booking)
            user = db.query(User).filter(User.id == booking.user_id).first()
            paid_count = db.query(Booking).filter(Booking.user_id == booking.user_id, Booking.status == "Paid").count()
            if user and paid_count >= 2 and not user.reward_granted:
                await reward_loyal_guest(db, user)
                user.reward_granted = True
                db.commit()
    else:
        transaction.status = "Failed"
        db.commit()
        user = db.query(User).filter(User.phone_number == normalize_phone(transaction.phone_number or "")).first()
        if user:
            await africastalking_service.send_sms(
                user.phone_number, f"Your M-Pesa payment was not completed: {result['result_description']}"
            )

    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.get("/status/{checkout_request_id}", dependencies=[Depends(require_admin)])
async def query_payment_status(checkout_request_id: str) -> dict[str, Any]:
    return await mpesa_service.query_status(checkout_request_id)


@router.get("/transactions", dependencies=[Depends(require_admin)])
async def list_transactions(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(Transaction).order_by(Transaction.created_at.desc()).all()
    return [
        {
            "id": row.id,
            "booking_id": row.booking_id,
            "checkout_request_id": row.checkout_request_id,
            "mpesa_receipt_number": row.mpesa_receipt_number,
            "amount": row.amount,
            "status": row.status,
            "phone_number": row.phone_number,
            "created_at": iso_utc(row.created_at),
        }
        for row in rows
    ]
