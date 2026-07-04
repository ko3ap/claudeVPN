"""Generic key-value store for admin-toggleable runtime settings.

Unlike app.config.settings (env-driven, frozen at process start), rows here
can be changed by admins at runtime without a restart.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.db.connection import get_conn


def get(key: str) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def get_bool(key: str, default: bool) -> bool:
    value = get(key)
    if value is None:
        return default
    return value == "1"


def get_int(key: str, default: int) -> int:
    value = get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def set(key: str, value: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
