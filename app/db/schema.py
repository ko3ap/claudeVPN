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

CREATE TABLE IF NOT EXISTS vpn_servers (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    docker_host        TEXT NOT NULL,   -- e.g. ssh://user@1.2.3.4 or unix:///var/run/docker.sock
    container_name     TEXT NOT NULL,
    interface_name     TEXT NOT NULL DEFAULT 'wg0',
    endpoint           TEXT NOT NULL,   -- host:port advertised to clients
    server_public_key  TEXT NOT NULL,
    subnet_cidr        TEXT NOT NULL,   -- e.g. 10.8.0.0/24 (client addresses allocated from here)
    dns                TEXT NOT NULL DEFAULT '1.1.1.1',
    extra_conf         TEXT NOT NULL DEFAULT '',
    max_clients        INTEGER NOT NULL DEFAULT 40,
    priority           INTEGER NOT NULL DEFAULT 100,
    enabled            INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS vpn_clients (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id  INTEGER NOT NULL UNIQUE REFERENCES users(telegram_id),
    server_id    INTEGER REFERENCES vpn_servers(id),
    private_key  TEXT NOT NULL,
    public_key   TEXT NOT NULL,
    address      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active', -- active|frozen|deleted
    managed      INTEGER NOT NULL DEFAULT 1,      -- 0 = legacy/imported, not under Docker lifecycle control
    legacy_conf_text TEXT,                        -- raw conf/key text for unmanaged legacy imports (server_id NULL)
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
"""


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


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(_TABLES)
        _seed_tariffs(conn)
        _seed_main_admin(conn)
    logger.info("Database initialized at %s", settings.db_path)
