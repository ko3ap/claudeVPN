from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.db.connection import get_conn


def create(
    *, payment_id: str, telegram_id: int, chat_id: int, tariff_key: str, amount: int
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO payments (payment_id, telegram_id, chat_id, tariff_key, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (payment_id, telegram_id, chat_id, tariff_key, amount, now),
        )


def set_status(payment_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE payments SET status = ? WHERE payment_id = ?", (status, payment_id)
        )


def get(payment_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM payments WHERE payment_id = ?", (payment_id,)
        ).fetchone()
        return dict(row) if row else None


def list_pending_created_after(cutoff: datetime) -> list[dict]:
    """Used on bot restart to resume polling for payments still within their timeout window."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM payments
            WHERE status = 'pending' AND datetime(created_at) >= datetime(?)
            """,
            (cutoff.isoformat(),),
        ).fetchall()
        return [dict(r) for r in rows]
