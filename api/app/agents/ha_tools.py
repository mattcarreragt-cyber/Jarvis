"""Outils Home Assistant — API REST locale (aucun GPU requis).

Lecture : libres.
Écriture (turn_on, turn_off, set_temperature) : exécution directe, sans
confirmation (choix utilisateur — commandes vocales/textuelles immédiates).
Token : HA_TOKEN (long-lived access token, Profil HA → Sécurité).
"""

from __future__ import annotations

import logging
import os
import re
import time
import unicodedata
from pathlib import Path

import httpx
import yaml

from app.config import settings
from app.contracts import SideEffect, ToolResult, ToolSpec

logger = logging.getLogger("jarvis.ha")

# Domaines contrôlables par défaut — source unique, partagée avec ha_agent.
CONTROLLABLE_DOMAINS = [
    "light", "switch", "media_player", "cover", "climate",
    "water_heater", "fan", "input_boolean",
]

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


def _singular(t: str) -> str:
    """Pluriel → singulier approximatif (volets→volet, lumieres→lumiere).
    Appliqué des deux côtés (alias ET message), donc toujours cohérent."""
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def _tokens(s: str) -> list[str]:
    return [_singular(t) for t in _norm(s).split() if t]


# Caches : alias (invalidé sur mtime) et index des états HA (TTL court).
_alias_cache: tuple[str, float, dict] | None = None
_states_cache: tuple[float, list[dict]] | None = None
_STATES_TTL = 60.0  # les friendly_name ne changent quasiment jamais


def _reset_caches() -> None:
    """Vide les caches (utilisé par les tests)."""
    global _alias_cache, _states_cache
    _alias_cache = None
    _states_cache = None


def _load_aliases() -> dict:
    global _alias_cache
    for cand in _ALIAS_CANDIDATES:
        if cand and Path(cand).is_file():
            try:
                mtime = os.path.getmtime(cand)
                if _alias_cache and _alias_cache[0] == cand and _alias_cache[1] == mtime:
                    return _alias_cache[2]
                with open(cand) as f:
                    data = yaml.safe_load(f) or {}
                _alias_cache = (cand, mtime, data)
                return data
            except Exception as e:
                logger.warning("ha_aliases.yaml illisible: %s", e)
            break
    return {}


async def _all_states() -> list[dict] | None:
    """États HA avec cache TTL — évite de re-télécharger 370 entités par message."""
    global _states_cache
    now = time.monotonic()
    if _states_cache and now - _states_cache[0] < _STATES_TTL:
        return _states_cache[1]
    res = await get_states(limit=0)
    if not res.ok:
        return None
    states = res.data.get("states", [])
    _states_cache = (now, states)
    return states


# Ensembles normalisés (accents retirés + singularisés) — mêmes règles que
# les tokens du message, pour que la comparaison soit cohérente.
_ACTION_TOKENS = {t for w in _ACTION_WORDS for t in _tokens(w)}
_FILLER_TOKENS = {t for w in _FILLER_WORDS for t in _tokens(w)}


def _target_tokens(message: str) -> list[str]:
    """Tokens de la cible : message moins les mots d'action et de remplissage."""
    return [t for t in _tokens(message)
            if t not in _ACTION_TOKENS and t not in _FILLER_TOKENS]


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
    domains = cfg.get("controllable_domains") or CONTROLLABLE_DOMAINS
    states = await _all_states()
    if states is None:
        return [], ""

    scored: list[tuple[int, str, str]] = []
    for s in states:
        eid = s["entity_id"]
        if eid.split(".")[0] not in domains:
            continue
        name_tokens = set(_tokens(s.get("friendly_name") or eid))
        score = sum(1 for t in target if t in name_tokens)
        if score:
            scored.append((score, eid, s.get("friendly_name") or eid))
    if not scored:
        return [], ""
    top = max(sc for sc, _, _ in scored)
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


async def turn_on(entity_id: str | list[str]) -> ToolResult:
    """Allume une ou plusieurs entités HA (un seul appel de service)."""
    return await _call_service("homeassistant", "turn_on", {"entity_id": entity_id})


async def turn_off(entity_id: str | list[str]) -> ToolResult:
    """Éteint une ou plusieurs entités HA (un seul appel de service)."""
    return await _call_service("homeassistant", "turn_off", {"entity_id": entity_id})


async def set_temperature(entity_id: str | list[str], temperature: float) -> ToolResult:
    """Règle la consigne de température (climate OU water_heater — le service
    est choisi selon le domaine de l'entité)."""
    ids = entity_id if isinstance(entity_id, list) else [entity_id]
    domain = ids[0].split(".")[0]
    if domain not in ("climate", "water_heater"):
        return ToolResult(ok=False, error=f"{ids[0]} n'est pas un thermostat (domaine {domain})")
    return await _call_service(domain, "set_temperature",
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
