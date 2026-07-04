"""One-time import of the old bot's data (new/legacy_data/*.sql) into the new
database. Run manually, once, after deploying this rewrite:

    python -m scripts.migrate_legacy_data

What it does:
  - Carries over each legacy user's remaining subscription days as an
    'active' (paid) subscription. The old schema's `is_trial` flag is set to
    1 by the old code on *any* purchase (not just real trials — see
    Database.py's update_subscription), so it can't reliably tell trial and
    paid users apart. We treat all migrated time as a paid subscription (the
    safer assumption) and use the old flag only to mark `trial_used`, so
    nobody gets a second free trial they've effectively already had.
  - If a user has a real WireGuard key stored (old `users.vpn_key`), it's
    imported as an *unmanaged* legacy vpn_clients row (server_id=NULL,
    managed=0) — the physical key keeps working, but this bot won't try to
    freeze/reactivate it via Docker since it doesn't know which physical
    server it lives on. Once you register that server with /addserver, an
    admin can migrate the user onto managed infrastructure by hand if needed.
  - Safe to re-run: any user who already has a non-'none' subscription in the
    new database is skipped rather than overwritten.
"""
from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import BASE_DIR
from app.db import subscriptions as subs_repo
from app.db import users as users_repo
from app.db import vpn_clients as clients_repo
from app.db.schema import init_db
from app.vpn.host import public_key_from_private

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

LEGACY_USERS_DB = BASE_DIR / "legacy_data" / "vpn_users.sql"


def _parse_conf(conf_text: str) -> tuple[str | None, str | None]:
    private_match = re.search(r"PrivateKey\s*=\s*(\S+)", conf_text)
    address_match = re.search(r"Address\s*=\s*([\d.]+)", conf_text)
    private_key = private_match.group(1) if private_match else None
    address = address_match.group(1) if address_match else None
    return private_key, address


def migrate() -> None:
    if not LEGACY_USERS_DB.exists():
        logger.info("No legacy_data/vpn_users.sql found — nothing to migrate.")
        return

    init_db()

    conn = sqlite3.connect(LEGACY_USERS_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT user_id, is_sub_active, days_remaining, is_trial, vpn_key, key_name, username FROM users"
    ).fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    migrated, skipped = 0, 0

    for row in rows:
        telegram_id = row["user_id"]
        existing = subs_repo.get(telegram_id)
        if existing and existing["status"] != "none":
            logger.info("User %s already has subscription data in the new DB — skipping.", telegram_id)
            skipped += 1
            continue

        users_repo.upsert_user(telegram_id, row["username"], None)
        subs_repo.ensure_row(telegram_id)

        days_remaining = row["days_remaining"] or 0
        has_time_left = bool(row["is_sub_active"]) and days_remaining > 0

        if has_time_left:
            subs_repo.set_active(telegram_id, now + timedelta(days=days_remaining))
        # trial_used=1 in the legacy DB really means "touched the trial/pay flow at
        # least once" (see module docstring) — treat that as trial_used here too.
        if row["is_trial"]:
            subs_repo.mark_trial_used(telegram_id)

        vpn_key = row["vpn_key"]
        if vpn_key and not clients_repo.get_by_user(telegram_id):
            private_key, address = _parse_conf(vpn_key)
            if private_key and address:
                try:
                    public_key = public_key_from_private(private_key)
                    client = clients_repo.create(
                        telegram_id=telegram_id,
                        server_id=None,
                        private_key=private_key,
                        public_key=public_key,
                        address=address,
                        managed=False,
                        legacy_conf_text=vpn_key,
                    )
                    if not has_time_left:
                        clients_repo.mark_frozen(telegram_id)
                    logger.info("Imported legacy VPN client for user %s (%s)", telegram_id, address)
                except Exception as e:
                    logger.warning("Could not parse/import legacy key for user %s: %s", telegram_id, e)
            else:
                logger.warning("Legacy vpn_key for user %s doesn't look like a WireGuard conf — skipped.", telegram_id)

        migrated += 1
        logger.info(
            "Migrated user %s: days_remaining=%s trial_used=%s",
            telegram_id, days_remaining, bool(row["is_trial"]),
        )

    logger.info("Migration complete: %d migrated, %d skipped.", migrated, skipped)


if __name__ == "__main__":
    migrate()
