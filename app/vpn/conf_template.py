"""Renders a client-facing WireGuard .conf file for the single VPN server."""
from __future__ import annotations

from app.config import settings


def render_client_conf(*, private_key: str, address: str) -> str:
    return (
        "[Interface]\n"
        f"PrivateKey = {private_key}\n"
        f"Address = {address}/32\n"
        f"DNS = {settings.vpn_dns}\n"
        "\n"
        "[Peer]\n"
        f"PublicKey = {settings.vpn_server_public_key}\n"
        f"Endpoint = {settings.vpn_endpoint}\n"
        "AllowedIPs = 0.0.0.0/0, ::/0\n"
        "PersistentKeepalive = 25\n"
    )
