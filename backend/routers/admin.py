from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Booking, ChatMessage, Property, Transaction, User
from schemas import AdminReplyRequest
from services.africastalking_service import africastalking_service
from utils import iso_utc

router = APIRouter(prefix="/admin", tags=["admin dashboard"])


@router.get("/stats")
async def dashboard_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    total_users = db.query(func.count(User.id)).scalar() or 0
    booking_count = db.query(func.count(Booking.id)).scalar() or 0
    paid_count = db.query(func.count(Booking.id)).filter(Booking.status == "Paid").scalar() or 0
    pending_count = db.query(func.count(Booking.id)).filter(Booking.status == "Pending").scalar() or 0
    successful = db.query(Transaction).filter(Transaction.status == "Success").all()
    total_revenue = sum(transaction.amount or 0 for transaction in successful)

    today = date.today()
    revenue_by_day = []
    for days_ago in range(6, -1, -1):
        day = today - timedelta(days=days_ago)
        amount = sum(
            transaction.amount or 0
            for transaction in successful
            if transaction.created_at and transaction.created_at.date() == day
        )
        revenue_by_day.append({"date": day.isoformat(), "revenue": round(amount, 2)})

    by_platform = db.query(User.platform, func.count(User.id)).group_by(User.platform).all()
    by_status = db.query(Booking.status, func.count(Booking.id)).group_by(Booking.status).all()

    return {
        "total_revenue": round(total_revenue, 2),
        "active_bookings": paid_count + pending_count,
        "total_users": total_users,
        "total_chats": db.query(func.count(ChatMessage.id)).scalar() or 0,
        "total_transactions": db.query(func.count(Transaction.id)).scalar() or 0,
        "successful_payments": len(successful),
        "conversion_rate": round((paid_count / booking_count * 100) if booking_count else 0, 1),
        "revenue_by_day": revenue_by_day,
        "users_by_platform": [{"platform": platform, "count": count} for platform, count in by_platform],
        "bookings_by_status": [{"status": status, "count": count} for status, count in by_status],
    }


@router.get("/bookings")
async def list_bookings(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = (
        db.query(Booking, User, Property)
        .join(User, Booking.user_id == User.id)
        .join(Property, Booking.property_id == Property.id)
        .order_by(Booking.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": booking.id,
            "guest_name": user.display_name,
            "phone_number": user.phone_number,
            "platform": user.platform,
            "property_name": prop.name,
            "location": prop.location,
            "check_in": booking.check_in,
            "check_out": booking.check_out,
            "guests": booking.guests,
            "status": booking.status,
            "total_amount": booking.total_amount,
            "created_at": iso_utc(booking.created_at),
        }
        for booking, user, prop in rows
    ]


@router.get("/users")
async def list_users(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
    counts = dict(db.query(Booking.user_id, func.count(Booking.id)).group_by(Booking.user_id).all())
    return [
        {
            "id": user.id,
            "phone_number": user.phone_number,
            "platform": user.platform,
            "display_name": user.display_name,
            "preferred_language": user.preferred_language,
            "created_at": iso_utc(user.created_at),
            "booking_count": counts.get(user.id, 0),
        }
        for user in rows
    ]


@router.get("/chats")
async def list_chats(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = (
        db.query(ChatMessage, User)
        .join(User, ChatMessage.user_id == User.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": message.id,
            "user_id": user.id,
            "guest_name": user.display_name,
            "phone_number": user.phone_number,
            "platform": message.platform,
            "direction": message.direction,
            "content": message.content,
            "intent": message.intent,
            "created_at": iso_utc(message.created_at),
        }
        for message, user in rows
    ]


@router.post("/chats/{user_id}/reply")
async def reply_to_chat(
    user_id: int,
    payload: AdminReplyRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    message = ChatMessage(
        user_id=user.id,
        platform=user.platform,
        direction="out",
        content=payload.message.strip(),
        intent="agent",
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    if user.platform in {"SMS", "USSD"}:
        await africastalking_service.send_sms(user.phone_number, payload.message.strip())

    return {
        "id": message.id,
        "user_id": user.id,
        "direction": message.direction,
        "content": message.content,
        "created_at": iso_utc(message.created_at),
    }


@router.get("/properties")
async def list_properties(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(Property).order_by(Property.rating.desc()).all()
    return [
        {
            "id": prop.id,
            "name": prop.name,
            "location": prop.location,
            "category": prop.category,
            "price_per_night": prop.price_per_night,
            "rating": prop.rating,
            "google_place_id": prop.google_place_id,
        }
        for prop in rows
    ]
