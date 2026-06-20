"""Endpoints de synchronisation Nextcloud."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.config import settings
from app.sources import nextcloud, state, sync

router = APIRouter(prefix="/api/nextcloud", tags=["nextcloud"])


@router.get("/status", dependencies=[Depends(require_api_key)])
async def status():
    """État de la sync : config, dernière exécution, volume indexé."""
    st = await state.stats()
    return {
        "configured":     nextcloud._configured(),
        "sync_enabled":   settings.nextcloud_sync_enabled,
        "sync_interval":  settings.nextcloud_sync_interval,
        "root":           settings.nextcloud_root,
        "running":        sync.is_running(),
        "last_result":    sync.last_result(),
        **st,
    }


@router.post("/ping", dependencies=[Depends(require_api_key)])
async def ping():
    """Teste la connexion + l'authentification Nextcloud."""
    ok = await nextcloud.ping()
    return {"reachable": ok}


@router.post("/sync", dependencies=[Depends(require_api_key)])
async def trigger_sync(background: bool = True):
    """Déclenche une sync manuelle. background=true → retourne immédiatement."""
    if not nextcloud._configured():
        return {"ok": False, "error": "Nextcloud non configuré"}
    if background:
        asyncio.create_task(sync.sync())
        return {"ok": True, "started": True, "background": True}
    result = await sync.sync()
    return result
