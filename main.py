"""Entrypoint: init the database, recover any in-flight payments, start the
background scheduler, and begin polling Telegram.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from app.bot.factory import build_bot, build_dispatcher
from app.config import settings
from app.db.schema import init_db
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)


async def _resume_pending_payments(bot) -> None:
    """On restart, resume polling any payment created within its timeout window."""
    from app.bot.routers.tariffs import track_payment
    from app.db import payments as payments_repo
    from app.services.subscription_service import now_utc

    cutoff = now_utc() - timedelta(seconds=settings.payment_poll_timeout_seconds)
    pending = payments_repo.list_pending_created_after(cutoff)
    for payment in pending:
        asyncio.create_task(
            track_payment(
                bot,
                payment["payment_id"],
                payment["telegram_id"],
                payment["chat_id"],
                payment["tariff_key"],
            )
        )
    if pending:
        logger.info("Resumed polling for %d pending payment(s)", len(pending))


async def main() -> None:
    setup_logging()
    init_db()

    bot = build_bot()
    dp = build_dispatcher()

    await _resume_pending_payments(bot)

    from app.scheduler.jobs import scheduler_loop

    asyncio.create_task(scheduler_loop(bot))

    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
