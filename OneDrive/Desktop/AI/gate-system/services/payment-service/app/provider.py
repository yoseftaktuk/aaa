import uuid


class CardProvider:
    async def create_checkout(self, *, transaction_id: uuid.UUID, amount_cents: int, currency: str) -> str:
        raise NotImplementedError

    async def refund(self, *, reference: str, amount_cents: int) -> None:
        raise NotImplementedError


class StubCardProvider(CardProvider):
    async def create_checkout(self, *, transaction_id: uuid.UUID, amount_cents: int, currency: str) -> str:
        # In dev, the dashboard can "simulate success" via webhook endpoint.
        return f"/payments/dev/checkout/{transaction_id}"

    async def refund(self, *, reference: str, amount_cents: int) -> None:
        return None


def get_provider(name: str) -> CardProvider:
    if name == "stub":
        return StubCardProvider()
    raise ValueError(f"unknown provider: {name}")

