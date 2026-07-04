"""Business rules for trial activation, purchases, extensions, and expiry.

This is the seam between Telegram handlers and the DB/VPN layers — handlers
should never touch app.db or app.vpn directly, only this module.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.db import pricing as pricing_repo
from app.db import settings as settings_repo
from app.db import subscriptions as subs_repo
from app.vpn.manager import AcquiredClient, VpnManager, vpn_manager

logger = logging.getLogger(__name__)


class TrialAlreadyUsedError(RuntimeError):
    pass


class AlreadySubscribedError(RuntimeError):
    """Raised when trying to start a trial while a paid subscription is already active."""


class TrialDisabledError(RuntimeError):
    """Raised when an admin has globally disabled the trial period."""


@dataclass
class PurchaseResult:
    acquired: AcquiredClient
    new_expires_at: datetime
    extended: bool  # True if added on top of existing time, False if started fresh


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse(dt: Optional[str]) -> Optional[datetime]:
    if not dt:
        return None
    parsed = datetime.fromisoformat(dt)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def days_left(expires_at: Optional[str], now: Optional[datetime] = None) -> int:
    parsed = _parse(expires_at)
    if not parsed:
        return 0
    now = now or now_utc()
    remaining = parsed - now
    if remaining.total_seconds() <= 0:
        return 0
    whole_days = remaining.days
    return whole_days + 1 if remaining.seconds > 0 or remaining.microseconds > 0 else whole_days


def get_view(telegram_id: int) -> dict:
    """Everything needed to render 'My subscription' / admin lookup screens."""
    sub = subs_repo.ensure_row(telegram_id)
    return {
        "status": sub["status"],
        "is_trial": sub["status"] == "trial",
        "expires_at": sub["expires_at"],
        "days_left": days_left(sub["expires_at"]),
        "trial_used": bool(sub["trial_used"]),
    }


def activate_trial(telegram_id: int, manager: VpnManager = vpn_manager) -> PurchaseResult:
    if not settings_repo.get_bool("trial_enabled", True):
        raise TrialDisabledError()

    sub = subs_repo.ensure_row(telegram_id)
    if sub["trial_used"]:
        raise TrialAlreadyUsedError()
    if sub["status"] == "active":
        raise AlreadySubscribedError()

    expires_at = now_utc() + timedelta(days=settings.trial_days)
    acquired = manager.acquire_client(telegram_id)
    subs_repo.set_trial(telegram_id, expires_at)
    return PurchaseResult(acquired=acquired, new_expires_at=expires_at, extended=False)


def activate_purchase(
    telegram_id: int, tariff_key: str, manager: VpnManager = vpn_manager
) -> PurchaseResult:
    tariff = pricing_repo.get(tariff_key)
    if not tariff:
        raise ValueError(f"Unknown tariff: {tariff_key}")

    sub = subs_repo.ensure_row(telegram_id)
    now = now_utc()
    extended = False

    if sub["status"] == "active":
        # Accumulate: add the new period on top of whatever time is left.
        current_expiry = _parse(sub["expires_at"]) or now
        base = max(current_expiry, now)
        new_expires_at = base + timedelta(days=tariff["days"])
        extended = True
    else:
        # Trial time (if any) is discarded — the paid period starts fresh from now.
        new_expires_at = now + timedelta(days=tariff["days"])

    acquired = manager.acquire_client(telegram_id)
    subs_repo.set_active(telegram_id, new_expires_at)
    return PurchaseResult(acquired=acquired, new_expires_at=new_expires_at, extended=extended)


def change_time(
    telegram_id: int, delta_days: int, manager: VpnManager = vpn_manager
) -> Optional[datetime]:
    """Admin utility: shift a user's expiry by delta_days (+/-).

    Returns the new expiry, or None if the change expired the subscription.
    """
    sub = subs_repo.ensure_row(telegram_id)
    now = now_utc()
    current_expiry = _parse(sub["expires_at"])
    base = current_expiry if (current_expiry and current_expiry > now) else now
    new_expires_at = base + timedelta(days=delta_days)

    if new_expires_at <= now:
        manager.freeze_client(telegram_id)
        subs_repo.expire(telegram_id)
        return None

    if sub["status"] != "active":
        manager.acquire_client(telegram_id)
    subs_repo.set_active(telegram_id, new_expires_at)
    return new_expires_at


def expire_subscription(telegram_id: int, manager: VpnManager = vpn_manager) -> None:
    manager.freeze_client(telegram_id)
    subs_repo.expire(telegram_id)


def has_capacity_for(telegram_id: int, manager: VpnManager = vpn_manager) -> bool:
    """Pre-flight check so routers can avoid charging a user into a dead end.

    Not authoritative — capacity can still change before fulfillment, which is
    why activate_purchase/activate_trial re-check for real via acquire_client.
    """
    return manager.has_capacity_for(telegram_id)
