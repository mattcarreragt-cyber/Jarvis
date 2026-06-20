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
    """Retourne 'xl' (RunPod), 'deep' ou 'fast' selon les mots-clés du message."""
    from app.config import settings
    data = _load()
    policy = data.get("chat_policy", {})
    msg_lower = message.lower()
    # 'xl' uniquement si RunPod est activé (gros modèle cloud)
    if settings.runpod_enabled:
        xl = policy.get("xl_triggers", [])
        if any(t in msg_lower for t in xl):
            return "xl"
    if any(t in msg_lower for t in policy.get("deep_triggers", [])):
        return "deep"
    return policy.get("default", "fast")


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

    # ── 3e palier : RunPod (GPU cloud) ────────────────────────────────────
    if machine == "runpod":
        from app.orchestration import runpod
        res = await runpod.ensure_runpod(cap.get("backend"))
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error"), "machine": machine,
                    "backend": cap.get("backend"), "model": cap.get("model"), "gpu": gpu}
        return {"ok": True, "machine": machine, "backend": cap.get("backend"),
                "model": cap.get("model"), "gpu": gpu, "vram_gb": cap.get("vram_gb"),
                "base_url": res["base_url"], "workflow": cap.get("workflow")}

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
        # Budget VRAM (GPU 8 Go) : libère la place si nécessaire.
        await _free_vram_for(cap)

    return {
        "ok":      True,
        "machine": machine,
        "backend": cap.get("backend"),
        "model":   cap.get("model"),
        "gpu":     gpu,
        "vram_gb": cap.get("vram_gb"),
        "workflow": cap.get("workflow"),
    }


async def _free_vram_for(cap: dict[str, Any]) -> None:
    """Libère de la VRAM avant de charger la capacité demandée (best-effort).

    - Capacité `exclusive` (ex. image/ComfyUI) : décharge TOUS les modèles Ollama,
      car ComfyUI et Ollama ne partagent pas la même VRAM visible.
    - Sinon : si l'empreinte cumulée dépasserait le budget, décharge les LLM
      résidents (Ollama recharge à la demande ; OLLAMA_MAX_LOADED_MODELS=1
      recommandé côté Kubuntu, voir KUBUNTU_SETUP.md).
    """
    from app.llm import ollama

    data = _load()
    budget = data.get("vram_budget_gb", 8)
    need = cap.get("vram_gb", 0) or 0

    if cap.get("exclusive"):
        freed = await ollama.unload_all()
        if freed:
            logger.info("VRAM : %d modèle(s) Ollama déchargé(s) pour capacité exclusive", freed)
        return

    # Backend ollama : Ollama gère lui-même l'éviction LLM↔LLM si MAX_LOADED_MODELS=1.
    # On intervient seulement si d'AUTRES modèles résidents + le besoin > budget.
    if cap.get("backend") == "ollama":
        target = cap.get("model")
        loaded = await ollama.ps()
        # Si le modèle cible est déjà chargé, rien à faire.
        if any((m.get("name") or m.get("model")) == target for m in loaded):
            return
        used_others = sum(
            m.get("size_vram", 0) / 1e9
            for m in loaded
            if (m.get("name") or m.get("model")) != target
        )
        if used_others + need > budget and loaded:
            freed = await ollama.unload_all()
            logger.info("VRAM : budget dépassé (%.1f+%.1f>%d) → %d modèle(s) déchargé(s)",
                        used_others, need, budget, freed)
