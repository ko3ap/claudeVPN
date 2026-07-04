"""Payment provider protocol — lets the bot support additional providers later
(e.g. CryptoPay, Telegram Stars) alongside YooKassa without touching callers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaymentLink:
    payment_id: str
    url: str


class PaymentProvider(Protocol):
    def create_payment(self, *, amount: int, description: str, metadata: dict) -> PaymentLink:
        ...

    def get_status(self, payment_id: str) -> str:
        """Returns one of: 'pending', 'succeeded', 'canceled'."""
        ...
