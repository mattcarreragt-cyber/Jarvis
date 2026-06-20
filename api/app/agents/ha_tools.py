"""Outils Home Assistant — API REST locale (aucun GPU requis).

Lecture : libres.
Écriture (turn_on, turn_off, call_service) : retournent needs_confirmation.
Token : HA_TOKEN (long-lived access token, Profil HA → Sécurité).
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.contracts import SideEffect, ToolResult, ToolSpec

logger = logging.getLogger("jarvis.ha")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.ha_token}",
        "Content-Type": "application/json",
    }


def _base() -> str:
    return settings.ha_url.rstrip("/")


async def get_states(domain: str | None = None) -> ToolResult:
    """Retourne tous les états HA, filtrés par domaine si fourni."""
    if not settings.ha_token:
        return ToolResult(ok=False, error="HA_TOKEN non configuré")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{_base()}/api/states", headers=_headers())
            r.raise_for_status()
        states = r.json()
        if domain:
            states = [s for s in states if s["entity_id"].startswith(f"{domain}.")]
        # On garde les champs essentiels pour ne pas surcharger le contexte
        slim = [
            {
                "entity_id": s["entity_id"],
                "state": s["state"],
                "friendly_name": s.get("attributes", {}).get("friendly_name"),
            }
            for s in states[:50]
        ]
        return ToolResult(ok=True, data={"states": slim, "total": len(states)})
    except httpx.ConnectError:
        return ToolResult(ok=False, error=f"Home Assistant injoignable ({_base()})")
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


async def get_entity(entity_id: str) -> ToolResult:
    """Retourne l'état complet d'une entité."""
    if not settings.ha_token:
        return ToolResult(ok=False, error="HA_TOKEN non configuré")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{_base()}/api/states/{entity_id}", headers=_headers())
            if r.status_code == 404:
                return ToolResult(ok=False, error=f"Entité {entity_id} introuvable")
            r.raise_for_status()
        s = r.json()
        return ToolResult(ok=True, data={
            "entity_id": s["entity_id"],
            "state": s["state"],
            "attributes": s.get("attributes", {}),
            "last_changed": s.get("last_changed"),
        })
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


async def turn_on(entity_id: str) -> ToolResult:
    """Allume une entité HA (lumière, switch, etc.)."""
    return await _call_service("homeassistant", "turn_on", {"entity_id": entity_id})


async def turn_off(entity_id: str) -> ToolResult:
    """Éteint une entité HA."""
    return await _call_service("homeassistant", "turn_off", {"entity_id": entity_id})


async def call_service(domain: str, service: str, data: dict) -> ToolResult:
    """Appelle un service HA arbitraire."""
    return await _call_service(domain, service, data)


async def _call_service(domain: str, service: str, data: dict) -> ToolResult:
    if not settings.ha_token:
        return ToolResult(ok=False, error="HA_TOKEN non configuré")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(
                f"{_base()}/api/services/{domain}/{service}",
                headers=_headers(),
                json=data,
            )
            r.raise_for_status()
        return ToolResult(ok=True, data={"called": f"{domain}.{service}", "data": data})
    except httpx.ConnectError:
        return ToolResult(ok=False, error=f"Home Assistant injoignable ({_base()})")
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


HANDLERS = {
    "ha.get_states":    lambda: get_states(),      # async — appelé avec await par l'agent
    "ha.get_entity":    get_entity,
    "ha.turn_on":       turn_on,
    "ha.turn_off":      turn_off,
    "ha.call_service":  call_service,
}

SPECS = [
    ToolSpec(name="ha.get_states",   description="Liste les entités HA (lumières, capteurs, switches…)",
             required_permissions=["ha:read"],  side_effects=SideEffect.none),
    ToolSpec(name="ha.get_entity",   description="État détaillé d'une entité HA spécifique",
             parameters={"entity_id": {"type": "string"}},
             required_permissions=["ha:read"],  side_effects=SideEffect.none),
    ToolSpec(name="ha.turn_on",      description="Allume une entité (lumière, switch, etc.)",
             parameters={"entity_id": {"type": "string"}},
             required_permissions=["ha:write"], side_effects=SideEffect.write),
    ToolSpec(name="ha.turn_off",     description="Éteint une entité",
             parameters={"entity_id": {"type": "string"}},
             required_permissions=["ha:write"], side_effects=SideEffect.write),
    ToolSpec(name="ha.call_service", description="Appelle un service HA arbitraire",
             required_permissions=["ha:write"], side_effects=SideEffect.write),
]
