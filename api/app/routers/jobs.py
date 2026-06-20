"""Endpoint de suivi des jobs de génération (vidéo, …)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.media import jobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", dependencies=[Depends(require_api_key)])
async def list_all():
    """Liste les jobs (génération vidéo en cours/terminés), récents d'abord."""
    items = await jobs.list_jobs()
    return {"jobs": items, "running": sum(1 for j in items if j["state"] == "running")}
