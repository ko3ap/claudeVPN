"""Table definitions and idempotent migrations, applied on startup."""
from __future__ import annotations

import logging
import sqlite3

from app.config import DEFAULT_TARIFFS, settings
from app.db.connection import get_conn

logger = logging.getLogger(__name__)

_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    telegram_id             INTEGER PRIMARY KEY REFERENCES users(telegram_id),
    status                  TEXT NOT NULL DEFAULT 'none', -- none|trial|active
    expires_at              TEXT,
    trial_used              INTEGER NOT NULL DEFAULT 0,
    trial_warned            INTEGER NOT NULL DEFAULT 0,
    reminder_last_sent_date TEXT
);

CREATE TABLE IF NOT EXISTS vpn_clients (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id  INTEGER NOT NULL UNIQUE REFERENCES users(telegram_id),
    private_key  TEXT NOT NULL,
    public_key   TEXT NOT NULL,
    address      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active', -- active|frozen|deleted
    managed      INTEGER NOT NULL DEFAULT 1,      -- 0 = legacy/imported, not under the VPN lifecycle
    legacy_conf_text TEXT,                        -- raw conf/key text for unmanaged legacy imports
    created_at   TEXT NOT NULL,
    frozen_at    TEXT
);

CREATE TABLE IF NOT EXISTS tariffs (
    key        TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    days       INTEGER NOT NULL,
    price      INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
    telegram_id INTEGER PRIMARY KEY,
    username    TEXT,
    added_by    INTEGER,
    added_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id  TEXT PRIMARY KEY,
    telegram_id INTEGER NOT NULL,
    chat_id     INTEGER NOT NULL,
    tariff_key  TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending', -- pending|succeeded|canceled|expired
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ephemeral_messages (
    chat_id    INTEGER PRIMARY KEY,
    message_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vpn_key_pool (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    private_key TEXT NOT NULL,
    public_key  TEXT NOT NULL,
    address     TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);
"""

_DEFAULT_SETTINGS = {
    "trial_enabled": "1",
    "vpn_pool_enabled": "1",
    "vpn_pool_buffer_size": "5",
}


def _seed_tariffs(conn: sqlite3.Connection) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    for tariff in DEFAULT_TARIFFS:
        conn.execute(
            "INSERT OR IGNORE INTO tariffs (key, label, days, price, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (tariff.key, tariff.label, tariff.days, tariff.price, now),
        )


def _seed_main_admin(conn: sqlite3.Connection) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO admins (telegram_id, username, added_by, added_at) "
        "VALUES (?, ?, ?, ?)",
        (settings.main_admin_id, settings.main_admin_username, settings.main_admin_id, now),
    )


def _seed_settings(conn: sqlite3.Connection) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    for key, value in _DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now),
        )


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate_drop_multi_server(conn: sqlite3.Connection) -> None:
    """The multi-server architecture (vpn_servers + server_id on vpn_clients/vpn_key_pool)
    was replaced by a single native WireGuard interface on this host. Renames any
    old-shape tables out of the way so the CREATE TABLE IF NOT EXISTS statements below
    can (re)create them in the new shape, then copies over any existing rows.
    """
    existing_tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }

    if "vpn_clients" in existing_tables and "server_id" in _table_columns(conn, "vpn_clients"):
        conn.execute("ALTER TABLE vpn_clients RENAME TO vpn_clients_old")
        conn.executescript(_TABLES)  # recreates vpn_clients in the new shape (and any other missing tables)
        conn.execute(
            """
            INSERT INTO vpn_clients
                (id, telegram_id, private_key, public_key, address, status, managed, legacy_conf_text, created_at, frozen_at)
            SELECT id, telegram_id, private_key, public_key, address, status, managed, legacy_conf_text, created_at, frozen_at
            FROM vpn_clients_old
            """
        )
        conn.execute("DROP TABLE vpn_clients_old")
        logger.info("Migrated vpn_clients: dropped server_id column")

    if "vpn_key_pool" in existing_tables and "server_id" in _table_columns(conn, "vpn_key_pool"):
        conn.execute("ALTER TABLE vpn_key_pool RENAME TO vpn_key_pool_old")
        conn.executescript(_TABLES)
        conn.execute(
            """
            INSERT OR IGNORE INTO vpn_key_pool (id, private_key, public_key, address, created_at)
            SELECT id, private_key, public_key, address, created_at FROM vpn_key_pool_old
            """
        )
        conn.execute("DROP TABLE vpn_key_pool_old")
        logger.info("Migrated vpn_key_pool: dropped server_id column")

    if "vpn_servers" in existing_tables:
        conn.execute("DROP TABLE vpn_servers")
        logger.info("Dropped vpn_servers table (multi-server support removed)")


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(_TABLES)
        _migrate_drop_multi_server(conn)
        _seed_tariffs(conn)
        _seed_main_admin(conn)
        _seed_settings(conn)
    logger.info("Database initialized at %s", settings.db_path)
