"""Outils Home Assistant — API REST locale (aucun GPU requis).

Lecture : libres.
Écriture (turn_on, turn_off, call_service) : retournent needs_confirmation.
Token : HA_TOKEN (long-lived access token, Profil HA → Sécurité).
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from pathlib import Path

import httpx
import yaml

from app.config import settings
from app.contracts import SideEffect, ToolResult, ToolSpec

logger = logging.getLogger("jarvis.ha")

# ─── Résolution langage naturel → entités HA (alias + nom convivial) ─────────

# Mots d'action / de remplissage retirés avant d'identifier la cible.
_ACTION_WORDS = {
    "allume", "allumer", "allumes", "allumé", "allumée", "allumés", "allumées",
    "active", "activer", "actives", "ouvre", "ouvrir", "ouvres", "démarre", "demarre",
    "lance", "lancer", "mets", "met", "mettre", "marche", "on",
    "éteins", "eteins", "éteindre", "eteindre", "éteint", "eteint", "coupe", "couper",
    "ferme", "fermer", "fermes", "arrête", "arrete", "arrêter", "stop", "off", "arret", "arrêt",
    "turn", "switch",
}
_FILLER_WORDS = {
    "la", "le", "les", "l", "du", "de", "des", "d", "un", "une", "au", "aux",
    "mon", "ma", "mes", "ce", "cet", "cette", "ces", "dans", "et",
    "stp", "svp", "jarvis", "veux", "peux", "tu", "je", "s", "il", "te", "plait", "plaît",
}

_ALIAS_CANDIDATES = [
    os.getenv("HA_ALIASES_PATH"),
    "/app/config/ha_aliases.yaml",
    str(Path(__file__).resolve().parent.parent.parent.parent / "config" / "ha_aliases.yaml"),
]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", s)


def _tokens(s: str) -> list[str]:
    return [t for t in _norm(s).split() if t]


def _load_aliases() -> dict:
    for cand in _ALIAS_CANDIDATES:
        if cand and Path(cand).is_file():
            try:
                with open(cand) as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning("ha_aliases.yaml illisible: %s", e)
            break
    return {}


def _target_tokens(message: str) -> list[str]:
    """Tokens de la cible : message moins les mots d'action et de remplissage."""
    return [t for t in _tokens(message)
            if t not in _ACTION_WORDS and t not in _FILLER_WORDS]


async def resolve_entities(message: str) -> tuple[list[str], str]:
    """Traduit une demande en langage naturel en liste d'entity_id.

    1) Alias déclarés dans config/ha_aliases.yaml (prioritaires).
    2) Sinon, correspondance par nom convivial (friendly_name) des entités HA
       des domaines contrôlables.
    Retourne (entity_ids, label_lisible). Liste vide si rien trouvé.
    """
    cfg = _load_aliases()
    msg_tokens = set(_tokens(message))

    # 1) Alias : tous les mots de l'alias présents dans le message.
    best_alias, best_len = None, 0
    for phrase, ents in (cfg.get("aliases") or {}).items():
        atoks = set(_tokens(phrase))
        if atoks and atoks <= msg_tokens and len(atoks) > best_len:
            best_alias, best_len = (phrase, ents), len(atoks)
    if best_alias:
        phrase, ents = best_alias
        ids = ents if isinstance(ents, list) else [ents]
        return [str(e) for e in ids], phrase

    # 2) Nom convivial : on cherche les entités dont le friendly_name partage
    #    le plus de mots avec la cible.
    target = _target_tokens(message)
    if not target:
        return [], ""
    domains = cfg.get("controllable_domains") or [
        "light", "switch", "media_player", "cover", "climate", "fan", "input_boolean",
    ]
    res = await get_states(limit=0)
    if not res.ok:
        return [], ""

    scored: list[tuple[int, str, str]] = []
    for s in res.data.get("states", []):
        eid = s["entity_id"]
        if eid.split(".")[0] not in domains:
            continue
        name_tokens = set(_tokens(s.get("friendly_name") or eid))
        score = sum(1 for t in target if t in name_tokens)
        if score:
            scored.append((score, eid, s.get("friendly_name") or eid))
    if not scored:
        return [], ""
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[0][0]
    winners = [(eid, name) for sc, eid, name in scored if sc == top]
    ids = [eid for eid, _ in winners]
    label = winners[0][1] if len(winners) == 1 else " + ".join(n for _, n in winners[:4])
    return ids, label


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.ha_token}",
        "Content-Type": "application/json",
    }


def _base() -> str:
    return settings.ha_url.rstrip("/")


async def get_states(domain: str | None = None, limit: int = 50) -> ToolResult:
    """Retourne les états HA, filtrés par domaine si fourni (limit=0 → tous)."""
    if not settings.ha_token:
        return ToolResult(ok=False, error="HA_TOKEN non configuré")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{_base()}/api/states", headers=_headers())
            r.raise_for_status()
        states = r.json()
        if domain:
            states = [s for s in states if s["entity_id"].startswith(f"{domain}.")]
        sliced = states if limit <= 0 else states[:limit]
        # On garde les champs essentiels pour ne pas surcharger le contexte
        slim = [
            {
                "entity_id": s["entity_id"],
                "state": s["state"],
                "friendly_name": s.get("attributes", {}).get("friendly_name"),
            }
            for s in sliced
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


async def set_temperature(entity_id: str, temperature: float) -> ToolResult:
    """Règle la consigne de température d'un climate (chauffage/clim)."""
    return await _call_service("climate", "set_temperature",
                               {"entity_id": entity_id, "temperature": temperature})


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
    "ha.get_states":       lambda: get_states(),
    "ha.get_entity":       get_entity,
    "ha.turn_on":          turn_on,
    "ha.turn_off":         turn_off,
    "ha.set_temperature":  set_temperature,
    "ha.call_service":     call_service,
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
    ToolSpec(name="ha.set_temperature", description="Règle la consigne de température d'un thermostat ou clim",
             parameters={"entity_id": {"type": "string"}, "temperature": {"type": "number"}},
             required_permissions=["ha:write"], side_effects=SideEffect.write),
    ToolSpec(name="ha.call_service", description="Appelle un service HA arbitraire",
             required_permissions=["ha:write"], side_effects=SideEffect.write),
]
