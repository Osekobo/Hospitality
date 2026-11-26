from pydantic import BaseModel, Field


class STKPushRequest(BaseModel):
    phone_number: str = Field(min_length=7, max_length=16, pattern=r"^\+?\d{7,15}$")
    amount: float | None = Field(default=None, gt=0, le=1_000_000)
    booking_id: int | None = Field(default=None, gt=0)
    account_reference: str | None = Field(default=None, max_length=12)


class ChatRequest(BaseModel):
    phone_number: str = Field(min_length=7, max_length=16, pattern=r"^\+?\d{7,15}$")
    platform: str = Field(default="WA", min_length=2, max_length=10, pattern=r"^[A-Za-z]+$")
    message: str = Field(min_length=1, max_length=2000)
    name: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, pattern=r"^(en|sw)$")


class AdminReplyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
