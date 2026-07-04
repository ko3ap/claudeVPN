"""Background payment polling — replaces the old "Check payment" button.

One asyncio task per pending payment checks its status every few seconds
(matching egor/payment.py's wait_for_payment interval) until it succeeds, is
canceled, or times out. The bot never requires the user to confirm anything.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from app.config import settings
from app.db import payments as payments_repo
from app.payments.base import PaymentProvider

logger = logging.getLogger(__name__)

OnSucceeded = Callable[[], Awaitable[None]]
OnTerminalFailure = Callable[[str], Awaitable[None]]


async def poll_payment(
    provider: PaymentProvider,
    payment_id: str,
    *,
    on_succeeded: OnSucceeded,
    on_terminal_failure: Optional[OnTerminalFailure] = None,
    interval: Optional[int] = None,
    timeout: Optional[int] = None,
) -> None:
    interval = interval or settings.payment_poll_interval_seconds
    timeout = timeout or settings.payment_poll_timeout_seconds
    elapsed = 0

    while elapsed < timeout:
        await asyncio.sleep(interval)
        elapsed += interval
        try:
            status = await asyncio.to_thread(provider.get_status, payment_id)
        except Exception as e:
            logger.warning("Error polling payment %s: %s", payment_id, e)
            continue

        if status == "succeeded":
            payments_repo.set_status(payment_id, "succeeded")
            await on_succeeded()
            return
        if status == "canceled":
            payments_repo.set_status(payment_id, "canceled")
            if on_terminal_failure:
                await on_terminal_failure("canceled")
            return

    payments_repo.set_status(payment_id, "expired")
    logger.info("Payment %s timed out after %ss", payment_id, timeout)
    if on_terminal_failure:
        await on_terminal_failure("expired")
