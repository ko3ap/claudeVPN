from __future__ import annotations

import logging
import uuid

from yookassa import Configuration, Payment

from app.config import settings
from app.payments.base import PaymentLink

logger = logging.getLogger(__name__)

Configuration.account_id = settings.yookassa_shop_id
Configuration.secret_key = settings.yookassa_secret_key

_STATUS_MAP = {
    "succeeded": "succeeded",
    "canceled": "canceled",
    "pending": "pending",
    "waiting_for_capture": "pending",
}


class YookassaProvider:
    def create_payment(self, *, amount: int, description: str, metadata: dict) -> PaymentLink:
        payment = Payment.create(
            {
                "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": settings.yookassa_return_url},
                "capture": True,
                "description": description,
                "metadata": metadata,
            },
            uuid.uuid4(),
        )
        logger.info("Payment created: id=%s amount=%s", payment.id, amount)
        return PaymentLink(payment_id=payment.id, url=payment.confirmation.confirmation_url)

    def get_status(self, payment_id: str) -> str:
        try:
            payment = Payment.find_one(payment_id)
            return _STATUS_MAP.get(payment.status, "pending")
        except Exception as e:
            logger.warning("Failed to check payment %s: %s", payment_id, e)
            return "pending"


yookassa_provider = YookassaProvider()
