from __future__ import annotations

from typing import Optional

from app.db.connection import get_conn


def list_servers(enabled_only: bool = True) -> list[dict]:
    query = "SELECT * FROM vpn_servers"
    if enabled_only:
        query += " WHERE enabled = 1"
    query += " ORDER BY priority ASC, id ASC"
    with get_conn() as conn:
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]


def get_server(server_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM vpn_servers WHERE id = ?", (server_id,)
        ).fetchone()
        return dict(row) if row else None


def add_server(
    *,
    name: str,
    docker_host: str,
    container_name: str,
    interface_name: str,
    endpoint: str,
    server_public_key: str,
    subnet_cidr: str,
    dns: str,
    extra_conf: str = "",
    max_clients: int,
    priority: int = 100,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO vpn_servers
                (name, docker_host, container_name, interface_name, endpoint,
                 server_public_key, subnet_cidr, dns, extra_conf, max_clients, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name, docker_host, container_name, interface_name, endpoint,
                server_public_key, subnet_cidr, dns, extra_conf, max_clients, priority,
            ),
        )
        return cur.lastrowid


def set_enabled(server_id: int, enabled: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE vpn_servers SET enabled = ? WHERE id = ?", (int(enabled), server_id)
        )


def count_occupied_slots(server_id: int) -> int:
    """Active + frozen clients occupy a slot; frozen ones keep their reserved config for 10 days."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n FROM vpn_clients
            WHERE server_id = ? AND status IN ('active', 'frozen')
            """,
            (server_id,),
        ).fetchone()
        return row["n"]


def used_addresses(server_id: int) -> set[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT address FROM vpn_clients WHERE server_id = ? AND status != 'deleted'",
            (server_id,),
        ).fetchall()
        return {r["address"] for r in rows}
