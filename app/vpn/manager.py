"""Capacity-aware orchestration across all VPN servers.

Picks a server with a free slot, creates/reactivates/freezes/purges WireGuard
clients, and keeps the DB in sync with what's live on each server. Servers are
tried in priority order; when one is full the next is used automatically.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from ipaddress import ip_network
from typing import Callable, Optional

from app.db import servers as servers_repo
from app.db import settings as settings_repo
from app.db import vpn_clients as clients_repo
from app.db import vpn_pool as vpn_pool_repo
from app.vpn.conf_template import render_client_conf
from app.vpn.host import WireGuardHost, generate_keypair, host_for_server

logger = logging.getLogger(__name__)

HostFactory = Callable[[dict], WireGuardHost]


class NoCapacityError(RuntimeError):
    """Raised when no enabled server has a free slot for a new client."""


@dataclass
class AcquiredClient:
    client: dict
    server: Optional[dict]
    conf_text: str
    reactivated: bool


class VpnManager:
    def __init__(self, host_factory: HostFactory = host_for_server):
        self._host_factory = host_factory

    def _allocate_address(self, server: dict) -> str:
        network = ip_network(server["subnet_cidr"], strict=False)
        used = servers_repo.used_addresses(server["id"])
        endpoint_host = server["endpoint"].rsplit(":", 1)[0]
        for addr_obj in network.hosts():
            addr = str(addr_obj)
            if addr not in used and addr != endpoint_host:
                return addr
        raise NoCapacityError(f"No free address left in {server['subnet_cidr']} on server '{server['name']}'")

    def _pick_server(self) -> Optional[dict]:
        for server in servers_repo.list_servers(enabled_only=True):
            occupied = servers_repo.count_occupied_slots(server["id"]) + vpn_pool_repo.count_available(server["id"])
            if occupied < server["max_clients"]:
                return server
        return None

    def has_capacity_for(self, telegram_id: int) -> bool:
        """Pre-flight, side-effect-free check for whether acquire_client would succeed."""
        existing = clients_repo.get_by_user(telegram_id)
        if existing and existing["status"] in ("active", "frozen"):
            return True
        return self._pick_server() is not None

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
        """Try handing out a pre-generated pool key (no live Docker call needed)."""
        for server in servers_repo.list_servers(enabled_only=True):
            entry = vpn_pool_repo.claim_one(server["id"])
            if not entry:
                continue
            client = clients_repo.create(
                telegram_id=telegram_id,
                server_id=server["id"],
                private_key=entry["private_key"],
                public_key=entry["public_key"],
                address=entry["address"],
            )
            conf_text = self._render(client, server)
            return AcquiredClient(client=client, server=server, conf_text=conf_text, reactivated=False)
        return None

    def _reuse_existing(self, existing: dict) -> AcquiredClient:
        server = servers_repo.get_server(existing["server_id"]) if existing["server_id"] else None
        was_frozen = existing["status"] == "frozen"

        if was_frozen:
            if not server or not existing["managed"]:
                raise NoCapacityError(
                    "This client has no managed server on file and can't be reactivated automatically."
                )
            host = self._host_factory(server)
            host.add_peer(existing["public_key"], existing["address"])
            clients_repo.mark_active(existing["telegram_id"])
            existing = clients_repo.get_by_user(existing["telegram_id"])

        conf_text = self._render(existing, server)
        return AcquiredClient(client=existing, server=server, conf_text=conf_text, reactivated=was_frozen)

    def _create_new(self, telegram_id: int) -> AcquiredClient:
        server = self._pick_server()
        if not server:
            raise NoCapacityError("All VPN servers are at capacity")

        private_key, public_key = generate_keypair()
        address = self._allocate_address(server)
        host = self._host_factory(server)
        host.add_peer(public_key, address)

        client = clients_repo.create(
            telegram_id=telegram_id,
            server_id=server["id"],
            private_key=private_key,
            public_key=public_key,
            address=address,
        )
        conf_text = self._render(client, server)
        return AcquiredClient(client=client, server=server, conf_text=conf_text, reactivated=False)

    def _render(self, client: dict, server: Optional[dict]) -> str:
        if server:
            return render_client_conf(server=server, private_key=client["private_key"], address=client["address"])
        return client.get("legacy_conf_text") or ""

    def freeze_client(self, telegram_id: int) -> None:
        """Stop traffic for a user's client but keep its config/key for the retention window."""
        client = clients_repo.get_by_user(telegram_id)
        if not client or client["status"] != "active":
            return
        if client["managed"] and client["server_id"]:
            server = servers_repo.get_server(client["server_id"])
            if server:
                host = self._host_factory(server)
                host.remove_peer(client["public_key"], client["address"])
            else:
                logger.warning("Client %s references missing server_id=%s", telegram_id, client["server_id"])
        clients_repo.mark_frozen(telegram_id)

    def purge_expired(self, cutoff: datetime) -> list[dict]:
        """Permanently delete clients that have been frozen past the retention window."""
        stale = clients_repo.list_frozen_older_than(cutoff)
        for client in stale:
            clients_repo.delete(client["telegram_id"])
            logger.info("Purged expired client for user %s (frozen since %s)", client["telegram_id"], client["frozen_at"])
        return stale

    def refill_pool(self) -> dict[int, int]:
        """Top up each enabled server's spare-key pool up to the configured buffer size.

        Runs from the scheduler, not the request path — this is what lets a
        purchase/trial claim a key instantly instead of waiting on a live
        Docker/SSH add_peer call.
        """
        created: dict[int, int] = {}
        if not settings_repo.get_bool("vpn_pool_enabled", True):
            return created

        buffer_size = settings_repo.get_int("vpn_pool_buffer_size", 5)
        for server in servers_repo.list_servers(enabled_only=True):
            server_id = server["id"]
            occupied = servers_repo.count_occupied_slots(server_id)
            room = server["max_clients"] - occupied
            target = min(buffer_size, max(room, 0))
            deficit = target - vpn_pool_repo.count_available(server_id)
            made = 0
            try:
                for _ in range(max(deficit, 0)):
                    private_key, public_key = generate_keypair()
                    address = self._allocate_address(server)
                    host = self._host_factory(server)
                    host.add_peer(public_key, address)
                    vpn_pool_repo.add(
                        server_id=server_id, private_key=private_key, public_key=public_key, address=address
                    )
                    made += 1
            except NoCapacityError:
                pass  # subnet exhausted for this server — move on to the next one
            except Exception as e:
                logger.error("Pool refill failed for server %s: %s", server["name"], e)
            if made:
                created[server_id] = made
        return created

    def get_conf_text(self, telegram_id: int) -> Optional[str]:
        client = clients_repo.get_by_user(telegram_id)
        if not client or client["status"] != "active":
            return None
        server = servers_repo.get_server(client["server_id"]) if client["server_id"] else None
        return self._render(client, server)


vpn_manager = VpnManager()
