"""Talks to the single native WireGuard interface on this host via wireguard-tools
(wg / wg-quick), run locally as root — no Docker, no SSH, since the bot process
already runs directly on the same machine as the VPN server.
"""
from __future__ import annotations

import base64
import logging
import subprocess

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from app.config import settings

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
    """Raised when a local wg/iptables operation fails outright."""


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise WireGuardHostError(
            f"`{' '.join(cmd)}` failed (exit={result.returncode}): {result.stderr.strip()}"
        )
    return result


def _save() -> None:
    """Best-effort: persist the running WG state to disk so it survives a restart.
    Non-fatal — the live change has already been applied at this point.
    """
    try:
        _run(["wg-quick", "save", settings.vpn_interface])
    except Exception as e:
        logger.warning("wg-quick save failed for %s: %s", settings.vpn_interface, e)


def add_peer(public_key: str, address: str) -> None:
    """Add (or re-add, for reactivation) a peer with a fixed client address."""
    try:
        _run(["wg", "set", settings.vpn_interface, "peer", public_key, "allowed-ips", f"{address}/32"])
        _save()
        logger.info("Peer added: %s -> %s on %s", public_key[:12], address, settings.vpn_interface)
    except WireGuardHostError:
        raise
    except Exception as e:
        raise WireGuardHostError(f"add_peer failed: {e}") from e


def remove_peer(public_key: str, address: str | None = None) -> bool:
    """Remove a peer and drop its in-flight traffic immediately.

    Returns True on success, False on any error (non-fatal — callers treat
    this as best-effort so scheduled sweeps keep going for other users).
    """
    try:
        if address:
            for chain in ("FORWARD", "INPUT"):
                try:
                    subprocess.run(
                        ["iptables", "-I", chain, "-s", address, "-j", "DROP"],
                        capture_output=True, text=True,
                    )
                except Exception as e:
                    logger.warning("iptables DROP failed for %s on %s: %s", address, chain, e)
        _run(["wg", "set", settings.vpn_interface, "peer", public_key, "remove"])
        _save()
        logger.info("Peer removed: %s on %s", public_key[:12], settings.vpn_interface)
        return True
    except Exception as e:
        logger.error("remove_peer failed for %s: %s", public_key[:12], e)
        return False
