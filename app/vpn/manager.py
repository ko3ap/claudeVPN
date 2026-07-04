"""Capacity-aware orchestration for the single native WireGuard interface on
this host. Creates/reactivates/freezes/purges WireGuard clients and keeps the
DB in sync with what's live on the interface.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from ipaddress import ip_network
from typing import Optional

from app.config import settings
from app.db import settings as settings_repo
from app.db import vpn_clients as clients_repo
from app.db import vpn_pool as vpn_pool_repo
from app.vpn import host
from app.vpn.conf_template import render_client_conf

logger = logging.getLogger(__name__)


class NoCapacityError(RuntimeError):
    """Raised when the VPN server has no free slot for a new client."""


@dataclass
class AcquiredClient:
    client: dict
    conf_text: str
    reactivated: bool


class VpnManager:
    def _allocate_address(self) -> str:
        network = ip_network(settings.vpn_subnet_cidr, strict=False)
        used = clients_repo.used_addresses() | vpn_pool_repo.used_addresses()
        used.add(settings.vpn_server_address)
        for addr_obj in network.hosts():
            addr = str(addr_obj)
            if addr not in used:
                return addr
        raise NoCapacityError(f"No free address left in {settings.vpn_subnet_cidr}")

    def has_capacity_for(self, telegram_id: int) -> bool:
        """Pre-flight, side-effect-free check for whether acquire_client would succeed."""
        existing = clients_repo.get_by_user(telegram_id)
        if existing and existing["status"] in ("active", "frozen"):
            return True
        occupied = clients_repo.count_occupied_slots() + vpn_pool_repo.count_available()
        return occupied < settings.vpn_max_clients

    def acquire_client(self, telegram_id: int) -> AcquiredClient:
        """Return a working client for this user, creating or reactivating one as needed."""
        existing = clients_repo.get_by_user(telegram_id)
        if existing and existing["status"] in ("active", "frozen"):
            return self._reuse_existing(existing)
        pooled = self._claim_from_pool(telegram_id)
        if pooled:
            return pooled
        return self._create_new(telegram_id)

    def _claim_from_pool(self, telegram_id: int) -> Optional[AcquiredClient]:
        """Try handing out a pre-generated pool key (no live wg call needed)."""
        entry = vpn_pool_repo.claim_one()
        if not entry:
            return None
        client = clients_repo.create(
            telegram_id=telegram_id,
            private_key=entry["private_key"],
            public_key=entry["public_key"],
            address=entry["address"],
        )
        conf_text = self._render(client)
        return AcquiredClient(client=client, conf_text=conf_text, reactivated=False)

    def _reuse_existing(self, existing: dict) -> AcquiredClient:
        was_frozen = existing["status"] == "frozen"

        if was_frozen:
            if not existing["managed"]:
                raise NoCapacityError(
                    "This client is not managed and can't be reactivated automatically."
                )
            host.add_peer(existing["public_key"], existing["address"])
            clients_repo.mark_active(existing["telegram_id"])
            existing = clients_repo.get_by_user(existing["telegram_id"])

        conf_text = self._render(existing)
        return AcquiredClient(client=existing, conf_text=conf_text, reactivated=was_frozen)

    def _create_new(self, telegram_id: int) -> AcquiredClient:
        occupied = clients_repo.count_occupied_slots() + vpn_pool_repo.count_available()
        if occupied >= settings.vpn_max_clients:
            raise NoCapacityError("VPN server is at capacity")

        private_key, public_key = host.generate_keypair()
        address = self._allocate_address()
        host.add_peer(public_key, address)

        client = clients_repo.create(
            telegram_id=telegram_id,
            private_key=private_key,
            public_key=public_key,
            address=address,
        )
        conf_text = self._render(client)
        return AcquiredClient(client=client, conf_text=conf_text, reactivated=False)

    def _render(self, client: dict) -> str:
        if client.get("managed", 1):
            return render_client_conf(private_key=client["private_key"], address=client["address"])
        return client.get("legacy_conf_text") or ""

    def freeze_client(self, telegram_id: int) -> None:
        """Stop traffic for a user's client but keep its config/key for the retention window."""
        client = clients_repo.get_by_user(telegram_id)
        if not client or client["status"] != "active":
            return
        if client["managed"]:
            host.remove_peer(client["public_key"], client["address"])
        clients_repo.mark_frozen(telegram_id)

    def purge_expired(self, cutoff: datetime) -> list[dict]:
        """Permanently delete clients that have been frozen past the retention window."""
        stale = clients_repo.list_frozen_older_than(cutoff)
        for client in stale:
            clients_repo.delete(client["telegram_id"])
            logger.info("Purged expired client for user %s (frozen since %s)", client["telegram_id"], client["frozen_at"])
        return stale

    def refill_pool(self) -> int:
        """Top up the spare-key pool up to the configured buffer size.

        Runs from the scheduler, not the request path — this is what lets a
        purchase/trial claim a key instantly instead of waiting on a live wg call.
        """
        if not settings_repo.get_bool("vpn_pool_enabled", True):
            return 0

        buffer_size = settings_repo.get_int("vpn_pool_buffer_size", 5)
        occupied = clients_repo.count_occupied_slots()
        room = settings.vpn_max_clients - occupied
        target = min(buffer_size, max(room, 0))
        deficit = target - vpn_pool_repo.count_available()

        made = 0
        try:
            for _ in range(max(deficit, 0)):
                private_key, public_key = host.generate_keypair()
                address = self._allocate_address()
                host.add_peer(public_key, address)
                vpn_pool_repo.add(private_key=private_key, public_key=public_key, address=address)
                made += 1
        except NoCapacityError:
            pass  # subnet exhausted
        except Exception as e:
            logger.error("Pool refill failed: %s", e)
        return made

    def get_conf_text(self, telegram_id: int) -> Optional[str]:
        client = clients_repo.get_by_user(telegram_id)
        if not client or client["status"] != "active":
            return None
        return self._render(client)


vpn_manager = VpnManager()
