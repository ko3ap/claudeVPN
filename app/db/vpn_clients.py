from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.db.connection import get_conn


def get_by_user(telegram_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM vpn_clients WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return dict(row) if row else None


def create(
    *,
    telegram_id: int,
    server_id: Optional[int],
    private_key: str,
    public_key: str,
    address: str,
    managed: bool = True,
    legacy_conf_text: Optional[str] = None,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO vpn_clients
                (telegram_id, server_id, private_key, public_key, address, status, managed, legacy_conf_text, created_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (telegram_id, server_id, private_key, public_key, address, int(managed), legacy_conf_text, now),
        )
    return get_by_user(telegram_id)


def mark_frozen(telegram_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE vpn_clients SET status = 'frozen', frozen_at = ? WHERE telegram_id = ?",
            (now, telegram_id),
        )


def mark_active(telegram_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE vpn_clients SET status = 'active', frozen_at = NULL WHERE telegram_id = ?",
            (telegram_id,),
        )


def delete(telegram_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM vpn_clients WHERE telegram_id = ?", (telegram_id,))


def list_frozen_older_than(cutoff: datetime) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM vpn_clients
            WHERE status = 'frozen' AND frozen_at IS NOT NULL
              AND datetime(frozen_at) <= datetime(?)
            """,
            (cutoff.isoformat(),),
        ).fetchall()
        return [dict(r) for r in rows]
