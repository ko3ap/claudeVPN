from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.db.connection import get_conn


def is_admin(telegram_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM admins WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return row is not None


def is_main_admin(username: Optional[str]) -> bool:
    return bool(username) and username.lower() == settings.main_admin_username.lower()


def list_admins() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM admins ORDER BY added_at ASC").fetchall()
        return [dict(r) for r in rows]


def add_admin(telegram_id: int, username: Optional[str], added_by: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO admins (telegram_id, username, added_by, added_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET username = excluded.username
            """,
            (telegram_id, username, added_by, now),
        )


def remove_admin(telegram_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
        return cur.rowcount > 0
