"""Streaming bureau distant — réveille Kubuntu (Wake-on-LAN) + statut Sunshine.

Sunshine (host) ↔ Moonlight (client). JARVIS réveille la machine et vérifie que
le service de streaming répond, puis indique comment se connecter.
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

from app.config import settings
from app.orchestration import wol

logger = logging.getLogger("jarvis.remote.stream")


def kubuntu_host() -> str:
    if settings.sunshine_host:
        return settings.sunshine_host
    h = urlparse(settings.kubuntu_url).hostname
    return h or "kubuntu"


async def is_sunshine_up(timeout: float = 3.0) -> bool:
    """Test TCP du port Sunshine/GameStream."""
    host, port = kubuntu_host(), settings.sunshine_port
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


def wake() -> bool:
    """Envoie le magic packet WoL à Kubuntu. False si MAC non configurée."""
    if not settings.kubuntu_mac:
        return False
    try:
        wol.send_magic_packet(settings.kubuntu_mac)
        return True
    except Exception as e:
        logger.warning("WoL: %s", e)
        return False


async def wake_and_wait(timeout: int = 120) -> dict:
    """Réveille Kubuntu et attend que Sunshine réponde. Retourne le statut."""
    woke = wake()
    host = kubuntu_host()
    if await is_sunshine_up():
        return {"woke": woke, "sunshine_up": True, "host": host, "port": settings.sunshine_port}

    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(4)
        if await is_sunshine_up():
            return {"woke": woke, "sunshine_up": True, "host": host,
                    "port": settings.sunshine_port}
    return {"woke": woke, "sunshine_up": False, "host": host,
            "port": settings.sunshine_port,
            "mac_set": bool(settings.kubuntu_mac)}
