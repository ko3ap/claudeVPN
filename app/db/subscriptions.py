"""Repository for the single per-user subscription record.

Each user has exactly one subscription row tracking whether they're on a
trial, an active paid period, or nothing — plus bookkeeping for the reminder
and trial-warning schedules.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from app.db.connection import get_conn


def _row_to_dict(row) -> Optional[dict]:
    return dict(row) if row else None


def get(telegram_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return _row_to_dict(row)


def ensure_row(telegram_id: int) -> dict:
    """Get the subscription row, creating a default 'none' row if missing."""
    existing = get(telegram_id)
    if existing:
        return existing
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO subscriptions (telegram_id, status) VALUES (?, 'none')",
            (telegram_id,),
        )
    return get(telegram_id)


def set_trial(telegram_id: int, expires_at: datetime) -> None:
    ensure_row(telegram_id)
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE subscriptions
            SET status = 'trial', expires_at = ?, trial_used = 1, trial_warned = 0
            WHERE telegram_id = ?
            """,
            (expires_at.isoformat(), telegram_id),
        )


def set_active(telegram_id: int, expires_at: datetime) -> None:
    ensure_row(telegram_id)
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE subscriptions
            SET status = 'active', expires_at = ?, reminder_last_sent_date = NULL
            WHERE telegram_id = ?
            """,
            (expires_at.isoformat(), telegram_id),
        )


def mark_trial_used(telegram_id: int) -> None:
    """Flag trial_used without touching status/expires_at (used by legacy data import)."""
    ensure_row(telegram_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE subscriptions SET trial_used = 1 WHERE telegram_id = ?", (telegram_id,)
        )


def expire(telegram_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE subscriptions SET status = 'none', expires_at = NULL WHERE telegram_id = ?",
            (telegram_id,),
        )


def mark_reminder_sent_today(telegram_id: int) -> None:
    today = date.today().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE subscriptions SET reminder_last_sent_date = ? WHERE telegram_id = ?",
            (today, telegram_id),
        )


def mark_trial_warned(telegram_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE subscriptions SET trial_warned = 1 WHERE telegram_id = ?",
            (telegram_id,),
        )


def get_expired(now: datetime) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM subscriptions
            WHERE status IN ('trial', 'active')
              AND expires_at IS NOT NULL
              AND datetime(expires_at) <= datetime(?)
            """,
            (now.isoformat(),),
        ).fetchall()
        return [dict(r) for r in rows]


def get_active_expiring_within_days(days: int, now: datetime) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM subscriptions
            WHERE status = 'active'
              AND expires_at IS NOT NULL
              AND datetime(expires_at) > datetime(?)
              AND datetime(expires_at) <= datetime(?, ?)
              AND (reminder_last_sent_date IS NULL OR reminder_last_sent_date != ?)
            """,
            (now.isoformat(), now.isoformat(), f"+{days} days", date.today().isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]


def get_trial_expiring_within_hours(hours: int, now: datetime) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM subscriptions
            WHERE status = 'trial'
              AND trial_warned = 0
              AND expires_at IS NOT NULL
              AND datetime(expires_at) > datetime(?)
              AND datetime(expires_at) <= datetime(?, ?)
            """,
            (now.isoformat(), now.isoformat(), f"+{hours} hours"),
        ).fetchall()
        return [dict(r) for r in rows]


def get_active_users() -> list[dict]:
    """Users with a currently active (paid or trial) subscription and days remaining > 0."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT s.*, u.username, u.full_name
            FROM subscriptions s
            JOIN users u ON u.telegram_id = s.telegram_id
            WHERE s.status IN ('trial', 'active')
              AND s.expires_at IS NOT NULL
              AND datetime(s.expires_at) > datetime('now')
            ORDER BY s.expires_at ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]
