"""Pre-generated, unassigned WireGuard keys for the single VPN server, ready to
be handed out without a live `wg`/systemd round-trip in the request path. Rows
are removed atomically on claim so two concurrent claims can never hand out
the same key.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.db.connection import get_conn


def count_available() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM vpn_key_pool").fetchone()
        return row["n"]


def add(*, private_key: str, public_key: str, address: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO vpn_key_pool (private_key, public_key, address, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (private_key, public_key, address, now),
        )
        row = conn.execute("SELECT * FROM vpn_key_pool WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def claim_one() -> Optional[dict]:
    """Atomically remove and return the oldest pool entry, or None if empty."""
    with get_conn() as conn:
        row = conn.execute(
            """
            DELETE FROM vpn_key_pool
            WHERE id = (SELECT id FROM vpn_key_pool ORDER BY id ASC LIMIT 1)
            RETURNING *
            """
        ).fetchone()
        return dict(row) if row else None


def used_addresses() -> set[str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT address FROM vpn_key_pool").fetchall()
        return {r["address"] for r in rows}
