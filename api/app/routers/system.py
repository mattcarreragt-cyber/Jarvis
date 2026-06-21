"""Endpoint Système — vue d'ensemble paliers, capacités, agents."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.config import settings
from app.llm import ollama
from app.orchestration import runpod
from app.orchestration.scheduler import list_capabilities
from app.registry import registry

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("", dependencies=[Depends(require_api_key)])
async def system_overview():
    """Paliers de calcul, capacités (modèles), agents enregistrés."""
    kubuntu_alive = await ollama.health()
    runpod_alive = False
    if settings.runpod_enabled and settings.runpod_ollama_url:
        runpod_alive = await runpod.is_backend_alive(
            settings.runpod_ollama_url.rstrip("/"), "ollama")

    paliers = [
        {"name": "Unraid", "role": "Orchestrateur (toujours allumé)",
         "status": "online"},
        {"name": "Kubuntu", "role": "GPU local 8 Go (LLM, images, vidéo, audio, STT)",
         "status": "online" if kubuntu_alive else "offline"},
        {"name": "RunPod", "role": "GPU cloud (gros modèles, vidéo HD)",
         "status": "online" if runpod_alive else
                   ("standby" if settings.runpod_enabled else "disabled")},
    ]

    return {
        "paliers": paliers,
        "capabilities": list_capabilities(),
        "agents": [{"name": s.name, "description": s.description} for s in registry.specs()],
    }
