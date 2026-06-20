"""Wake-on-LAN + health check du nœud de calcul Kubuntu.

Voir docs/08_ORCHESTRATION.md.
Kubuntu n'est réveillé QUE si la capacité demandée nécessite gpu=true + machine=kubuntu.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time

import httpx

from app.config import settings

logger = logging.getLogger("jarvis.wol")


def _build_magic_packet(mac: str) -> bytes:
    mac_clean = mac.replace(":", "").replace("-", "")
    if len(mac_clean) != 12:
        raise ValueError(f"Adresse MAC invalide : {mac}")
    mac_bytes = bytes.fromhex(mac_clean)
    return b"\xff" * 6 + mac_bytes * 16


def send_magic_packet(mac: str, broadcast: str = "255.255.255.255", port: int = 9) -> None:
    packet = _build_magic_packet(mac)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (broadcast, port))
    logger.info("Magic packet envoyé → %s", mac)


async def is_kubuntu_alive(timeout: float = 3.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{settings.kubuntu_url}/api/tags")
            return r.status_code < 500
    except Exception:
        return False


async def ensure_kubuntu(broadcast: str = "255.255.255.255") -> bool:
    """Vérifie Kubuntu, envoie WoL si absent. Retourne True si disponible."""
    if await is_kubuntu_alive():
        return True

    if not settings.kubuntu_wol_enabled:
        logger.warning("Kubuntu injoignable et WoL désactivé (KUBUNTU_WOL_ENABLED=false)")
        return False

    if not settings.kubuntu_mac:
        logger.error("KUBUNTU_MAC non configuré — impossible d'envoyer le magic packet")
        return False

    logger.info("Kubuntu hors ligne → envoi magic packet (WoL)")
    try:
        send_magic_packet(settings.kubuntu_mac, broadcast)
    except Exception as e:
        logger.error("Erreur WoL : %s", e)
        return False

    deadline = time.monotonic() + settings.kubuntu_wol_timeout
    while time.monotonic() < deadline:
        await asyncio.sleep(3)
        if await is_kubuntu_alive():
            logger.info("Kubuntu en ligne (réveil WoL réussi)")
            return True
        logger.debug("En attente du réveil Kubuntu…")

    logger.error("Kubuntu n'a pas répondu dans les %ds", settings.kubuntu_wol_timeout)
    return False
