from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.db.connection import get_conn


def get_all() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tariffs ORDER BY days ASC").fetchall()
        return [dict(r) for r in rows]


def get(key: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tariffs WHERE key = ?", (key,)).fetchone()
        return dict(row) if row else None


def update_price(key: str, new_price: int) -> Optional[int]:
    """Update a tariff's price. Returns the previous price, or None if the tariff doesn't exist."""
    current = get(key)
    if not current:
        return None
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE tariffs SET price = ?, updated_at = ? WHERE key = ?",
            (new_price, now, key),
        )
    return current["price"]
