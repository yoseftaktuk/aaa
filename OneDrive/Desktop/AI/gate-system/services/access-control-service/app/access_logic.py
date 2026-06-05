from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from .clients import ChipClient, HardwareClient
from .models import AccessLog
from .schemas import AccessDecisionResponse
from .settings import settings

logger = logging.getLogger(__name__)


class CashSession:
    def __init__(self) -> None:
        self._accumulated_cents = 0
        self._lock = asyncio.Lock()

    @property
    def accumulated_cents(self) -> int:
        return self._accumulated_cents

    async def add(self, amount_cents: int) -> int:
        async with self._lock:
            self._accumulated_cents += amount_cents
            return self._accumulated_cents

    async def take_fee(self, fee_cents: int) -> int:
        async with self._lock:
            paid = self._accumulated_cents
            self._accumulated_cents = max(0, self._accumulated_cents - fee_cents)
            return paid


async def process_chip_access(
    uid: str,
    db: AsyncSession,
    *,
    chip_client: ChipClient,
    hardware_client: HardwareClient,
    publish,
) -> AccessDecisionResponse:
    fee = settings.entrance_fee_cents
    door_seconds = settings.door_unlock_seconds
    ts = datetime.now(timezone.utc).isoformat()

    try:
        chip = await chip_client.validate(uid)
    except ValueError:
        log = AccessLog(chip_id=None, uid=uid, decision="denied", reason="unknown_chip", fee_cents=fee)
        db.add(log)
        await db.commit()
        await publish({"type": "access.denied", "uid": uid, "reason": "unknown_chip", "ts": ts})
        return AccessDecisionResponse(granted=False, reason="unknown_chip", chip_id=None, fee_cents=fee)

    if not chip.is_enabled:
        log = AccessLog(
            chip_id=chip.chip_id,
            uid=chip.uid,
            decision="denied",
            reason="chip_disabled",
            fee_cents=fee,
            balance_before_cents=chip.balance_cents,
            balance_after_cents=chip.balance_cents,
        )
        db.add(log)
        await db.commit()
        await publish(
            {
                "type": "access.denied",
                "uid": chip.uid,
                "chip_id": chip.chip_id,
                "reason": "chip_disabled",
                "balance_cents": chip.balance_cents,
                "ts": ts,
            }
        )
        return AccessDecisionResponse(
            granted=False,
            reason="chip_disabled",
            chip_id=chip.chip_id,
            fee_cents=fee,
            balance_before_cents=chip.balance_cents,
            balance_after_cents=chip.balance_cents,
        )

    if chip.balance_cents < fee:
        log = AccessLog(
            chip_id=chip.chip_id,
            uid=chip.uid,
            decision="denied",
            reason="insufficient_balance",
            fee_cents=fee,
            balance_before_cents=chip.balance_cents,
            balance_after_cents=chip.balance_cents,
        )
        db.add(log)
        await db.commit()
        await publish(
            {
                "type": "access.denied",
                "uid": chip.uid,
                "chip_id": chip.chip_id,
                "reason": "insufficient_balance",
                "balance_cents": chip.balance_cents,
                "fee_cents": fee,
                "ts": ts,
            }
        )
        return AccessDecisionResponse(
            granted=False,
            reason="insufficient_balance",
            chip_id=chip.chip_id,
            fee_cents=fee,
            balance_before_cents=chip.balance_cents,
            balance_after_cents=chip.balance_cents,
        )

    before = chip.balance_cents
    try:
        after = await chip_client.adjust_balance(
            chip_id=chip.chip_id,
            delta_cents=-fee,
            reason="entry_fee",
            description="entrance fee charged",
        )
    except ValueError:
        log = AccessLog(
            chip_id=chip.chip_id,
            uid=chip.uid,
            decision="denied",
            reason="insufficient_balance",
            fee_cents=fee,
            balance_before_cents=before,
            balance_after_cents=before,
        )
        db.add(log)
        await db.commit()
        await publish(
            {
                "type": "access.denied",
                "uid": chip.uid,
                "chip_id": chip.chip_id,
                "reason": "insufficient_balance",
                "balance_cents": before,
                "fee_cents": fee,
                "ts": ts,
            }
        )
        return AccessDecisionResponse(
            granted=False,
            reason="insufficient_balance",
            chip_id=chip.chip_id,
            fee_cents=fee,
            balance_before_cents=before,
            balance_after_cents=before,
        )

    await hardware_client.open_door(seconds=door_seconds)
    log = AccessLog(
        chip_id=chip.chip_id,
        uid=chip.uid,
        decision="granted",
        reason="ok",
        fee_cents=fee,
        balance_before_cents=before,
        balance_after_cents=after,
    )
    db.add(log)
    await db.commit()
    await publish(
        {
            "type": "access.granted",
            "uid": chip.uid,
            "chip_id": chip.chip_id,
            "method": "chip",
            "fee_cents": fee,
            "balance_after_cents": after,
            "ts": ts,
        }
    )
    return AccessDecisionResponse(
        granted=True,
        reason="ok",
        chip_id=chip.chip_id,
        fee_cents=fee,
        balance_before_cents=before,
        balance_after_cents=after,
    )


async def process_cash_inserted(
    amount_cents: int,
    db: AsyncSession,
    *,
    cash_session: CashSession,
    hardware_client: HardwareClient,
    publish,
) -> tuple[bool, int]:
    fee = settings.entrance_fee_cents
    door_seconds = settings.door_unlock_seconds
    ts = datetime.now(timezone.utc).isoformat()

    total = await cash_session.add(amount_cents)
    await publish(
        {
            "type": "cash.accumulated",
            "amount_cents": amount_cents,
            "total_cents": total,
            "required_cents": fee,
            "ts": ts,
        }
    )

    if total < fee:
        logger.info("cash_partial total_cents=%s required_cents=%s", total, fee)
        return False, total

    paid_total = await cash_session.take_fee(fee)
    remaining = paid_total - fee
    await hardware_client.open_door(seconds=door_seconds)
    log = AccessLog(
        chip_id=None,
        uid=None,
        decision="granted",
        reason="cash_paid",
        fee_cents=fee,
        balance_before_cents=paid_total,
        balance_after_cents=paid_total - fee,
    )
    db.add(log)
    await db.commit()
    await publish(
        {
            "type": "access.granted",
            "method": "cash",
            "reason": "cash_paid",
            "fee_cents": fee,
            "paid_total_cents": paid_total,
            "remaining_cents": remaining,
            "ts": ts,
        }
    )
    logger.info("cash_access_granted paid_total_cents=%s fee_cents=%s", paid_total, fee)
    return True, remaining
