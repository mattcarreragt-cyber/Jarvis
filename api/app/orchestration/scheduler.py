"""Capability Scheduler — résout capacité → backend, réveille Kubuntu si GPU requis.

Voir docs/08_ORCHESTRATION.md.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import os

import yaml

from app.orchestration.wol import ensure_kubuntu, is_kubuntu_alive

logger = logging.getLogger("jarvis.scheduler")

_HERE = Path(__file__).resolve()
# Candidats, dans l'ordre : variable d'env, volume conteneur, racine repo (dev).
_CANDIDATES = [
    os.getenv("CAPABILITIES_PATH"),
    "/app/config/capabilities.yaml",
    str(_HERE.parent.parent.parent / "config" / "capabilities.yaml"),   # api/config (volume)
    str(_HERE.parent.parent.parent.parent / "config" / "capabilities.yaml"),  # racine repo (dev)
]


def _resolve_path() -> Path:
    for cand in _CANDIDATES:
        if cand and Path(cand).is_file():
            return Path(cand)
    raise FileNotFoundError(
        f"capabilities.yaml introuvable. Cherché : {[c for c in _CANDIDATES if c]}"
    )


_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    global _cache
    if _cache is None:
        with open(_resolve_path()) as f:
            _cache = yaml.safe_load(f)
    return _cache


def reload() -> None:
    """Force le rechargement du fichier YAML (hot-reload sans redémarrage)."""
    global _cache
    _cache = None


def get_capability(name: str) -> dict[str, Any] | None:
    data = _load()
    return data.get("capabilities", {}).get(name)


def resolve_chat_hint(message: str) -> str:
    """Retourne 'fast' ou 'deep' selon les mots-clés du message."""
    data = _load()
    triggers = data.get("chat_policy", {}).get("deep_triggers", [])
    msg_lower = message.lower()
    if any(t in msg_lower for t in triggers):
        return "deep"
    return data.get("chat_policy", {}).get("default", "fast")


async def dispatch(capability: str) -> dict[str, Any]:
    """
    Résout une capacité et s'assure que le backend est disponible.
    Retourne un dict avec: ok, machine, backend, model, gpu, error?
    """
    cap = get_capability(capability)
    if cap is None:
        return {"ok": False, "error": f"Capacité inconnue: {capability}"}

    machine = cap.get("machine", "unraid")
    gpu     = cap.get("gpu", False)

    if machine == "kubuntu" and gpu:
        alive = await is_kubuntu_alive()
        if not alive:
            logger.info("Capacité %s requiert Kubuntu GPU — déclenchement WoL", capability)
            available = await ensure_kubuntu()
            if not available:
                return {
                    "ok":       False,
                    "error":    "Kubuntu indisponible (WoL échoué ou désactivé)",
                    "machine":  machine,
                    "backend":  cap.get("backend"),
                    "model":    cap.get("model"),
                    "gpu":      gpu,
                }

    return {
        "ok":      True,
        "machine": machine,
        "backend": cap.get("backend"),
        "model":   cap.get("model"),
        "gpu":     gpu,
    }
