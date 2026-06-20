"""RunPod — 3e palier de calcul (GPU cloud) pour les gros modèles.

Mode supporté : **Pod** (machine GPU louée exposant Ollama/ComfyUI en HTTP).
Le pod est démarré à la demande via l'API REST RunPod, puis arrêté manuellement
(ou via un cron RunPod) pour ne payer que l'usage.

Flux ensure_runpod(backend) :
1. URL du backend (ollama/comfyui) exposée par le pod (settings).
2. si déjà joignable → ok.
3. sinon démarre le pod (REST /pods/{id}/start) et attend qu'il réponde.

Best-effort : tout échec → {ok: False, error}. Le scheduler retombe alors sur
un message clair côté agent.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger("jarvis.runpod")

_REST = "https://rest.runpod.io/v1"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.runpod_api_key}"}


def _backend_url(backend: str) -> str:
    if backend == "ollama":
        return settings.runpod_ollama_url.rstrip("/")
    if backend == "comfyui":
        return settings.runpod_comfyui_url.rstrip("/")
    return ""


async def is_backend_alive(url: str, backend: str) -> bool:
    if not url:
        return False
    probe = "/api/tags" if backend == "ollama" else "/system_stats"
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r = await client.get(f"{url}{probe}")
            return r.status_code < 500
    except Exception:
        return False


async def pod_status() -> str | None:
    """desiredStatus du pod (RUNNING / EXITED / …) ou None si inconnu."""
    if not (settings.runpod_api_key and settings.runpod_pod_id):
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{_REST}/pods/{settings.runpod_pod_id}", headers=_headers())
            r.raise_for_status()
            return r.json().get("desiredStatus")
    except Exception as e:
        logger.warning("pod_status: %s", e)
        return None


async def start_pod() -> bool:
    if not (settings.runpod_api_key and settings.runpod_pod_id):
        return False
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{_REST}/pods/{settings.runpod_pod_id}/start", headers=_headers())
            return r.status_code < 400
    except Exception as e:
        logger.error("start_pod: %s", e)
        return False


async def stop_pod() -> bool:
    if not (settings.runpod_api_key and settings.runpod_pod_id):
        return False
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{_REST}/pods/{settings.runpod_pod_id}/stop", headers=_headers())
            return r.status_code < 400
    except Exception as e:
        logger.error("stop_pod: %s", e)
        return False


async def ensure_runpod(backend: str) -> dict:
    """Garantit qu'un backend RunPod est joignable. {ok, base_url?, error?}."""
    if not settings.runpod_enabled:
        return {"ok": False, "error": "RunPod désactivé (RUNPOD_ENABLED=false)"}

    url = _backend_url(backend)
    if not url:
        return {"ok": False, "error": f"URL RunPod {backend} non configurée"}

    if await is_backend_alive(url, backend):
        return {"ok": True, "base_url": url}

    # Démarrage du pod si possible
    if not (settings.runpod_api_key and settings.runpod_pod_id):
        return {"ok": False, "error": "Pod RunPod injoignable et démarrage non configuré "
                                      "(RUNPOD_API_KEY/RUNPOD_POD_ID)"}

    logger.info("Pod RunPod hors ligne → démarrage")
    if not await start_pod():
        return {"ok": False, "error": "Échec du démarrage du pod RunPod"}

    deadline = asyncio.get_event_loop().time() + settings.runpod_start_timeout
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(5)
        if await is_backend_alive(url, backend):
            logger.info("Pod RunPod en ligne (%s)", backend)
            return {"ok": True, "base_url": url}

    return {"ok": False, "error": f"Pod RunPod non prêt dans les {settings.runpod_start_timeout}s"}
