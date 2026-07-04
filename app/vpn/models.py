from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VpnServer:
    id: int
    name: str
    docker_host: str
    container_name: str
    interface_name: str
    endpoint: str
    server_public_key: str
    subnet_cidr: str
    dns: str
    extra_conf: str
    max_clients: int
    priority: int
    enabled: bool

    @classmethod
    def from_row(cls, row: dict) -> "VpnServer":
        return cls(
            id=row["id"],
            name=row["name"],
            docker_host=row["docker_host"],
            container_name=row["container_name"],
            interface_name=row["interface_name"],
            endpoint=row["endpoint"],
            server_public_key=row["server_public_key"],
            subnet_cidr=row["subnet_cidr"],
            dns=row["dns"],
            extra_conf=row["extra_conf"],
            max_clients=row["max_clients"],
            priority=row["priority"],
            enabled=bool(row["enabled"]),
        )


@dataclass(frozen=True)
class VpnClient:
    id: int
    telegram_id: int
    server_id: Optional[int]
    private_key: str
    public_key: str
    address: str
    status: str
    managed: bool
    created_at: str
    frozen_at: Optional[str]

    @classmethod
    def from_row(cls, row: dict) -> "VpnClient":
        return cls(
            id=row["id"],
            telegram_id=row["telegram_id"],
            server_id=row["server_id"],
            private_key=row["private_key"],
            public_key=row["public_key"],
            address=row["address"],
            status=row["status"],
            managed=bool(row["managed"]),
            created_at=row["created_at"],
            frozen_at=row["frozen_at"],
        )
