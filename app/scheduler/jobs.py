"""Background sweeps: expiry, reminders, trial warnings, and purging clients
that have been frozen past the retention window. One loop, run periodically —
modeled after egor/scheduler.py's structure (try/except per sweep so one
failure doesn't stop the others).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from aiogram import Bot

from app.config import settings
from app.db import subscriptions as subs_repo
from app.services import subscription_service, texts
from app.services.ui import send_persistent
from app.vpn.manager import vpn_manager

logger = logging.getLogger(__name__)


async def _sweep_expired(bot: Bot) -> None:
    now = subscription_service.now_utc()
    for sub in subs_repo.get_expired(now):
        telegram_id = sub["telegram_id"]
        try:
            subscription_service.expire_subscription(telegram_id)
            await send_persistent(bot, telegram_id, texts.subscription_expired())
        except Exception as e:
            logger.error("Failed to expire subscription for %s: %s", telegram_id, e)


async def _sweep_reminders(bot: Bot) -> None:
    now = subscription_service.now_utc()
    for sub in subs_repo.get_active_expiring_within_days(settings.reminder_days_before, now):
        telegram_id = sub["telegram_id"]
        days = subscription_service.days_left(sub["expires_at"], now)
        try:
            await send_persistent(bot, telegram_id, texts.expiry_reminder(days))
            subs_repo.mark_reminder_sent_today(telegram_id)
        except Exception as e:
            logger.warning("Failed to send reminder to %s: %s", telegram_id, e)


async def _sweep_trial_warnings(bot: Bot) -> None:
    now = subscription_service.now_utc()
    for sub in subs_repo.get_trial_expiring_within_hours(settings.trial_warning_hours_before, now):
        telegram_id = sub["telegram_id"]
        try:
            await send_persistent(bot, telegram_id, texts.trial_expiring_soon(settings.trial_warning_hours_before))
            subs_repo.mark_trial_warned(telegram_id)
        except Exception as e:
            logger.warning("Failed to send trial warning to %s: %s", telegram_id, e)


async def _sweep_purge(bot: Bot) -> None:
    now = subscription_service.now_utc()
    cutoff = now - timedelta(days=settings.frozen_client_retention_days)
    try:
        purged = vpn_manager.purge_expired(cutoff)
        if purged:
            logger.info("Purged %d expired VPN clients", len(purged))
    except Exception as e:
        logger.error("Failed to purge expired clients: %s", e)


async def run_all_sweeps(bot: Bot) -> None:
    for sweep in (_sweep_expired, _sweep_reminders, _sweep_trial_warnings, _sweep_purge):
        try:
            await sweep(bot)
        except Exception as e:
            logger.exception("Scheduler sweep %s failed: %s", sweep.__name__, e)


async def scheduler_loop(bot: Bot) -> None:
    logger.info("Scheduler started (interval=%ss)", settings.scheduler_interval_seconds)
    while True:
        await run_all_sweeps(bot)
        await asyncio.sleep(settings.scheduler_interval_seconds)
