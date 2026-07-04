"""Renders a client-facing WireGuard .conf file from server + client records."""
from __future__ import annotations


def render_client_conf(*, server: dict, private_key: str, address: str) -> str:
    extra = server.get("extra_conf") or ""
    if extra and not extra.startswith("\n"):
        extra = "\n" + extra
    return (
        "[Interface]\n"
        f"PrivateKey = {private_key}\n"
        f"Address = {address}/32\n"
        f"DNS = {server['dns']}"
        f"{extra}\n"
        "\n"
        "[Peer]\n"
        f"PublicKey = {server['server_public_key']}\n"
        f"Endpoint = {server['endpoint']}\n"
        "AllowedIPs = 0.0.0.0/0, ::/0\n"
        "PersistentKeepalive = 25\n"
    )
