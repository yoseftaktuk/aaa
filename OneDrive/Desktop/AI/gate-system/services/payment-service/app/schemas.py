import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateCardPaymentRequest(BaseModel):
    amount_cents: int = Field(gt=0, le=10_000_00)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    purpose: str = Field(default="recharge", max_length=30)
    chip_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class CreateCashPaymentRequest(BaseModel):
    amount_cents: int = Field(gt=0, le=10_000_00)
    purpose: str = Field(default="guest_entry", max_length=30)
    chip_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    amount_cents: int
    currency: str
    method: str
    status: str
    reference: str | None
    user_id: uuid.UUID | None
    chip_id: uuid.UUID | None
    purpose: str
    created_at: datetime
    updated_at: datetime


class PaymentIntentResponse(BaseModel):
    transaction: TransactionResponse
    checkout_url: str | None = None  # card flows


class WebhookEventRequest(BaseModel):
    transaction_id: uuid.UUID
    status: str = Field(pattern="^(succeeded|failed)$")
    reference: str | None = None


class RefundRequest(BaseModel):
    transaction_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=255)

