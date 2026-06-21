"""VPN Mullvad — statut (am.i.mullvad.net) + contrôle via CLI (SSH).

Deux niveaux :
- statut HTTP : reflète la sortie réseau de JARVIS (serveur Unraid) ;
- statut/contrôle CLI : via SSH sur un hôte où `mullvad` est installé
  (MULLVAD_SSH_HOST) — plus précis pour CET hôte.

Best-effort : pas de réseau / hôte non configuré → renvoie None.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger("jarvis.vpn.mullvad")

_AM_I = "https://am.i.mullvad.net/json"


def _host() -> dict | None:
    if not settings.mullvad_ssh_host:
        return None
    return {"hostname": settings.mullvad_ssh_host, "username": settings.mullvad_ssh_user,
            "port": settings.mullvad_ssh_port}


async def http_status() -> dict | None:
    """Statut vu depuis la sortie réseau de JARVIS."""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(_AM_I)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("am.i.mullvad: %s", e)
        return None


async def ssh_status() -> str | None:
    host = _host()
    if host is None:
        return None
    from app.cyber.ssh import run_once
    res = await run_once(host, "mullvad status 2>/dev/null")
    return res.get("output") if res.get("ok") else None


async def control(action: str, location: str | None = None) -> dict:
    """connect | disconnect | location <code>. Nécessite MULLVAD_SSH_HOST."""
    host = _host()
    if host is None:
        return {"ok": False, "error": "MULLVAD_SSH_HOST non configuré (contrôle indisponible)"}
    if action == "connect":
        cmd = "mullvad connect"
    elif action == "disconnect":
        cmd = "mullvad disconnect"
    elif action == "location" and location:
        cmd = f"mullvad relay set location {location} && mullvad connect"
    else:
        return {"ok": False, "error": "Action invalide"}
    from app.cyber.ssh import run_once
    res = await run_once(host, cmd)
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error")}
    return {"ok": True, "output": res.get("output", "")}
