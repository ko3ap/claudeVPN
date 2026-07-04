"""Centralized, environment-driven configuration.

Secrets and per-deployment values are read from the environment (populated from
a local `.env` file via python-dotenv). Nothing sensitive is hardcoded here —
only defaults that are safe to share (default tariffs, timings, etc.).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Tariff:
    key: str
    label: str
    days: int
    price: int


DEFAULT_TARIFFS: tuple[Tariff, ...] = (
    Tariff("1m", "1 месяц", 30, 199),
    Tariff("3m", "3 месяца", 90, 549),
    Tariff("6m", "6 месяцев", 180, 999),
    Tariff("12m", "12 месяцев", 365, 1799),
)


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.environ.get("BOT_TOKEN", ""))
    db_path: Path = field(
        default_factory=lambda: BASE_DIR / os.environ.get("DB_PATH", "data/bot.db")
    )

    # The one person who can manage other admins. Everyone else in the `admins`
    # table can use the rest of the admin panel.
    main_admin_username: str = field(
        default_factory=lambda: os.environ.get("MAIN_ADMIN_USERNAME", "ko3ap")
    )
    main_admin_id: int = field(
        default_factory=lambda: _env_int("MAIN_ADMIN_ID", 1009503906)
    )

    news_channel: str = field(
        default_factory=lambda: os.environ.get("NEWS_CHANNEL", "")
    )
    support_username: str = field(
        default_factory=lambda: os.environ.get("SUPPORT_USERNAME", "ko3ap")
    )

    yookassa_shop_id: str = field(
        default_factory=lambda: os.environ.get("YOOKASSA_SHOP_ID", "")
    )
    yookassa_secret_key: str = field(
        default_factory=lambda: os.environ.get("YOOKASSA_SECRET_KEY", "")
    )
    yookassa_return_url: str = field(
        default_factory=lambda: os.environ.get("YOOKASSA_RETURN_URL", "https://t.me/")
    )

    # Trial period
    trial_days: int = field(default_factory=lambda: _env_int("TRIAL_DAYS", 2))
    trial_warning_hours_before: int = field(
        default_factory=lambda: _env_int("TRIAL_WARNING_HOURS_BEFORE", 3)
    )

    # Reminders / lifecycle
    reminder_days_before: int = field(
        default_factory=lambda: _env_int("REMINDER_DAYS_BEFORE", 3)
    )
    frozen_client_retention_days: int = field(
        default_factory=lambda: _env_int("FROZEN_CLIENT_RETENTION_DAYS", 10)
    )
    scheduler_interval_seconds: int = field(
        default_factory=lambda: _env_int("SCHEDULER_INTERVAL_SECONDS", 900)
    )

    # Payment polling
    payment_poll_interval_seconds: int = field(
        default_factory=lambda: _env_int("PAYMENT_POLL_INTERVAL_SECONDS", 5)
    )
    payment_poll_timeout_seconds: int = field(
        default_factory=lambda: _env_int("PAYMENT_POLL_TIMEOUT_SECONDS", 1800)
    )

    # Single VPN server — a native WireGuard interface on this same host,
    # managed directly via wireguard-tools (no Docker, no multi-server pool).
    vpn_interface: str = field(
        default_factory=lambda: os.environ.get("VPN_INTERFACE", "wg1")
    )
    vpn_server_address: str = field(
        default_factory=lambda: os.environ.get("VPN_SERVER_ADDRESS", "10.10.0.1")
    )
    vpn_endpoint: str = field(
        default_factory=lambda: os.environ.get("VPN_ENDPOINT", "")
    )
    vpn_server_public_key: str = field(
        default_factory=lambda: os.environ.get("VPN_SERVER_PUBLIC_KEY", "")
    )
    vpn_subnet_cidr: str = field(
        default_factory=lambda: os.environ.get("VPN_SUBNET_CIDR", "10.10.0.0/24")
    )
    vpn_dns: str = field(
        default_factory=lambda: os.environ.get("VPN_DNS", "8.8.8.8")
    )
    vpn_max_clients: int = field(
        default_factory=lambda: _env_int("VPN_MAX_CLIENTS", 200)
    )

    require_channel_subscription: bool = field(
        default_factory=lambda: _env_bool("REQUIRE_CHANNEL_SUBSCRIPTION", False)
    )


settings = Settings()
