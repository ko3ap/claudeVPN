"""Tracks the last disposable ('ephemeral') message id per chat.

Used to auto-clean up obsolete UI: tariff menus, payment links, "checking..."
placeholders. Important messages (payment confirmations, expiry notices,
reminders) never go through this and are never auto-deleted.
"""
from __future__ import annotations

from typing import Optional

from app.db.connection import get_conn


def get(chat_id: int) -> Optional[int]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT message_id FROM ephemeral_messages WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return row["message_id"] if row else None


def set(chat_id: int, message_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO ephemeral_messages (chat_id, message_id) VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET message_id = excluded.message_id
            """,
            (chat_id, message_id),
        )


def clear(chat_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM ephemeral_messages WHERE chat_id = ?", (chat_id,))
