"""Endpoint statistiques d'usage."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.stats import get_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", dependencies=[Depends(require_api_key)])
async def stats():
    """Agrégats d'usage : totaux, agents les plus utilisés, outils, activité."""
    return await get_stats()
