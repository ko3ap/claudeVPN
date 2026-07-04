"""WireGuardHost — talks to a single VPN server's Docker daemon (local socket or
remote over SSH, e.g. base_url='ssh://user@1.2.3.4') to create/enable/disable
WireGuard peers on an AmneziaWG/WireGuard container.

Modeled after egor/vpn.py's disconnect_peer (docker-exec + iptables DROP), but
generalized to any server's docker host and extended with peer creation, which
egor's pool-of-pre-made-.conf approach never needed.
"""
from __future__ import annotations

import base64
import logging

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

logger = logging.getLogger(__name__)


def generate_keypair() -> tuple[str, str]:
    """Generate a WireGuard-compatible X25519 keypair. Returns (private_b64, public_b64)."""
    private_key = X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(private_bytes).decode(), base64.b64encode(public_bytes).decode()


def public_key_from_private(private_key_b64: str) -> str:
    """Derive the WireGuard public key for a stored private key (e.g. for legacy imports)."""
    raw = base64.b64decode(private_key_b64)
    private_key = X25519PrivateKey.from_private_bytes(raw)
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(public_bytes).decode()


class WireGuardHostError(RuntimeError):
    """Raised when a WireGuard/Docker operation against a server fails outright."""


class WireGuardHost:
    """Docker-exec operations against one VPN server's WireGuard container."""

    def __init__(self, docker_host: str, container_name: str, interface_name: str):
        self.docker_host = docker_host
        self.container_name = container_name
        self.interface_name = interface_name

    def _container(self):
        import docker

        client = docker.DockerClient(base_url=self.docker_host)
        return client.containers.get(self.container_name)

    def _exec(self, container, cmd: list[str]):
        result = container.exec_run(cmd, user="root", privileged=True)
        if result.exit_code != 0:
            raise WireGuardHostError(
                f"`{' '.join(cmd)}` failed (exit={result.exit_code}): "
                f"{result.output.decode(errors='ignore').strip()}"
            )
        return result

    def _persist(self, container) -> None:
        """Best-effort: save the running WG state to disk so it survives a container restart.
        Non-fatal — the live change has already been applied at this point.
        """
        try:
            self._exec(container, ["wg-quick", "save", self.interface_name])
        except Exception as e:
            logger.warning("wg-quick save failed on %s: %s", self.container_name, e)

    def add_peer(self, public_key: str, address: str) -> None:
        """Add (or re-add, for reactivation) a peer with a fixed client address."""
        try:
            container = self._container()
            self._exec(
                container,
                ["wg", "set", self.interface_name, "peer", public_key,
                 "allowed-ips", f"{address}/32"],
            )
            self._persist(container)
            logger.info("Peer added: %s -> %s on %s", public_key[:12], address, self.container_name)
        except WireGuardHostError:
            raise
        except Exception as e:
            raise WireGuardHostError(f"add_peer failed: {e}") from e

    def remove_peer(self, public_key: str, address: str | None = None) -> bool:
        """Remove a peer and drop its in-flight traffic immediately.

        Returns True on success, False on any error (non-fatal — callers treat
        this as best-effort so scheduled sweeps keep going for other users).
        """
        try:
            container = self._container()
            if address:
                for chain in ("FORWARD", "INPUT"):
                    try:
                        container.exec_run(
                            ["iptables", "-I", chain, "-s", address, "-j", "DROP"],
                            user="root",
                            privileged=True,
                        )
                    except Exception as e:
                        logger.warning("iptables DROP failed for %s on %s: %s", address, chain, e)
            self._exec(container, ["wg", "set", self.interface_name, "peer", public_key, "remove"])
            self._persist(container)
            logger.info("Peer removed: %s on %s", public_key[:12], self.container_name)
            return True
        except Exception as e:
            logger.error("remove_peer failed for %s: %s", public_key[:12], e)
            return False


def host_for_server(server: dict) -> WireGuardHost:
    return WireGuardHost(
        docker_host=server["docker_host"],
        container_name=server["container_name"],
        interface_name=server["interface_name"],
    )
