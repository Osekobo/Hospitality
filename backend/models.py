from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("platform", "phone_number", name="uq_user_platform_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(40), index=True)
    platform: Mapped[str] = mapped_column(String(10), default="WA", index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(5), default="en")
    reward_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="user")


class Property(TimestampMixin, Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    location: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(60), default="Hotel")
    price_per_night: Mapped[float] = mapped_column(Float, default=0.0)
    google_place_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    bookings: Mapped[list["Booking"]] = relationship(back_populates="property")


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    check_in: Mapped[str] = mapped_column(String(20))
    check_out: Mapped[str] = mapped_column(String(20))
    guests: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(
        Enum("Pending", "Paid", "Cancelled", name="booking_status"), default="Pending", index=True
    )
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    mpesa_checkout_request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    user: Mapped["User"] = relationship(back_populates="bookings")
    property: Mapped["Property"] = relationship(back_populates="bookings")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="booking")


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    mpesa_receipt_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    merchant_request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    checkout_request_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        Enum("Pending", "Success", "Failed", name="transaction_status"), default="Pending", index=True
    )
    result_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    booking: Mapped["Booking | None"] = relationship(back_populates="transactions")


class ChatMessage(TimestampMixin, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (UniqueConstraint("external_id", name="uq_chat_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(10), index=True)
    direction: Mapped[str] = mapped_column(String(4), index=True)
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    user: Mapped["User"] = relationship(back_populates="messages")
