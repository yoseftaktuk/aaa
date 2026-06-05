import json
import logging

import redis.asyncio as redis
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gate_shared.errors import AppError, ErrorResponse
from gate_shared.logging import configure_logging

from .db import engine, get_db
from .models import Base, RechargeOperation, Transaction
from .provider import get_provider
from .schemas import (
    CreateCardPaymentRequest,
    CreateCashPaymentRequest,
    PaymentIntentResponse,
    RefundRequest,
    TransactionResponse,
    WebhookEventRequest,
)
from .settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Payment Service",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

redis_client: redis.Redis | None = None
provider = get_provider(settings.payment_provider)


@app.on_event("startup")
async def startup() -> None:
    global redis_client
    configure_logging(settings.service_name, settings.log_level)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("startup_complete provider=%s", settings.payment_provider)


@app.on_event("shutdown")
async def shutdown() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


@app.exception_handler(AppError)
async def app_error_handler(_, exc: AppError):
    return JSONResponse(
        status_code=exc.http_status,
        content=ErrorResponse(code=exc.code, message=exc.message, details=exc.details).model_dump(),
    )


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": settings.service_name}


async def _publish(event: dict) -> None:
    if redis_client is None:
        return
    await redis_client.publish("payment.events", json.dumps(event))


def _tx_response(tx: Transaction) -> TransactionResponse:
    return TransactionResponse.model_validate(tx, from_attributes=True)


@app.post("/payments/card", response_model=PaymentIntentResponse, status_code=status.HTTP_201_CREATED)
async def create_card_payment(req: CreateCardPaymentRequest, db: AsyncSession = Depends(get_db)):
    tx = Transaction(
        amount_cents=req.amount_cents,
        currency=req.currency,
        method="card",
        status="pending",
        user_id=req.user_id,
        chip_id=req.chip_id,
        purpose=req.purpose,
    )
    db.add(tx)
    await db.flush()
    checkout_url = await provider.create_checkout(transaction_id=tx.id, amount_cents=tx.amount_cents, currency=tx.currency)
    await db.commit()
    await db.refresh(tx)
    await _publish({"type": "payment.created", "transaction_id": str(tx.id), "method": "card", "status": tx.status})
    return PaymentIntentResponse(transaction=_tx_response(tx), checkout_url=checkout_url)


@app.post("/payments/cash", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_cash_payment(req: CreateCashPaymentRequest, db: AsyncSession = Depends(get_db)):
    # Cash collection is confirmed by hardware-service events; this creates a pending record.
    tx = Transaction(
        amount_cents=req.amount_cents,
        currency="USD",
        method="cash",
        status="pending",
        user_id=req.user_id,
        chip_id=req.chip_id,
        purpose=req.purpose,
        reference=None,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    await _publish({"type": "cash_session.created", "transaction_id": str(tx.id), "amount_cents": tx.amount_cents})
    return _tx_response(tx)


@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str, db: AsyncSession = Depends(get_db)):
    tx = await db.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    return _tx_response(tx)


@app.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(db: AsyncSession = Depends(get_db), chip_id: str | None = None, user_id: str | None = None):
    stmt = select(Transaction).order_by(Transaction.created_at.desc())
    if chip_id:
        stmt = stmt.where(Transaction.chip_id == chip_id)
    if user_id:
        stmt = stmt.where(Transaction.user_id == user_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [_tx_response(r) for r in rows]


@app.post("/refunds", response_model=TransactionResponse)
async def refund(req: RefundRequest, db: AsyncSession = Depends(get_db)):
    tx = await db.get(Transaction, req.transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    if tx.status != "succeeded":
        raise AppError(code="not_refundable", message="Only succeeded transactions can be refunded", http_status=409)
    if tx.method == "card" and tx.reference:
        await provider.refund(reference=tx.reference, amount_cents=tx.amount_cents)
    tx.status = "refunded"
    await db.commit()
    await db.refresh(tx)
    await _publish({"type": "payment.refunded", "transaction_id": str(tx.id)})
    return _tx_response(tx)


# Provider callbacks / webhooks
@app.post("/webhooks/provider", status_code=204)
async def provider_webhook(
    event: WebhookEventRequest,
    x_webhook_secret: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    if x_webhook_secret != settings.payment_webhook_secret:
        raise HTTPException(status_code=401, detail="invalid_webhook_secret")
    tx = await db.get(Transaction, event.transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    tx.status = event.status
    if event.reference:
        tx.reference = event.reference
    await db.commit()
    await db.refresh(tx)
    await _publish({"type": "payment.updated", "transaction_id": str(tx.id), "status": tx.status, "purpose": tx.purpose})
    return None


# Dev convenience endpoint: simulate card success/failure by calling the webhook.
@app.post("/payments/dev/simulate/{transaction_id}/{status}", status_code=204, include_in_schema=False)
async def dev_simulate(transaction_id: str, status: str, db: AsyncSession = Depends(get_db)):
    if settings.environment not in ("dev", "test"):
        raise HTTPException(status_code=404, detail="not_found")
    if status not in ("succeeded", "failed"):
        raise HTTPException(status_code=400, detail="invalid_status")
    tx = await db.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    tx.status = status
    tx.reference = tx.reference or f"stub-{tx.id}"
    await db.commit()
    await db.refresh(tx)
    await _publish({"type": "payment.updated", "transaction_id": str(tx.id), "status": tx.status, "purpose": tx.purpose})
    return None


@app.post("/recharge", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_recharge_operation(chip_id: str, transaction_id: str, db: AsyncSession = Depends(get_db)):
    tx = await db.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    if tx.status != "succeeded":
        raise AppError(code="payment_not_succeeded", message="Payment must succeed before recharge", http_status=409)
    op = RechargeOperation(chip_id=chip_id, transaction_id=tx.id, amount_cents=tx.amount_cents, status="completed")
    db.add(op)
    await db.commit()
    await _publish({"type": "recharge.completed", "chip_id": chip_id, "transaction_id": str(tx.id), "amount_cents": tx.amount_cents})
    return {"status": "completed", "chip_id": chip_id, "amount_cents": tx.amount_cents}

