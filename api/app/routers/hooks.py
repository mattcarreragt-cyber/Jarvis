"""Endpoints webhooks — déclenchement externe (par token) + gestion (API key)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_api_key
from app.automation import hooks, runner, store

router = APIRouter(prefix="/api/hooks", tags=["hooks"])


# ── Déclenchement public (auth par token dans l'URL, pas d'API key) ──────────

async def execute_hook(hook: dict) -> None:
    """Exécute le message d'un hook et notifie le résultat (tâche de fond)."""
    text = await runner._run_prompt(hook["message"])
    await store.add_notification(text, source=f"webhook:{hook['label']}")
    await hooks.mark_triggered(hook["id"])


@router.post("/{token}")
async def trigger(token: str):
    """Déclenche le message pré-configuré d'un webhook. Appelable par HA, cron, etc."""
    hook = await hooks.get_by_token(token)
    if hook is None or not hook.get("enabled", True):
        raise HTTPException(404, "Webhook inconnu ou désactivé")
    asyncio.create_task(execute_hook(hook))
    return {"ok": True, "queued": True, "label": hook["label"]}


# ── Gestion (protégée par API key) ───────────────────────────────────────────

class HookIn(BaseModel):
    label: str
    message: str


@router.get("", dependencies=[Depends(require_api_key)])
async def list_all():
    return {"hooks": await hooks.list_hooks()}


@router.post("", dependencies=[Depends(require_api_key)])
async def create(body: HookIn):
    h = await hooks.create_hook(body.label, body.message)
    if h is None:
        raise HTTPException(503, "Base indisponible")
    return h


@router.delete("/{hook_id}", dependencies=[Depends(require_api_key)])
async def delete(hook_id: str):
    return {"ok": await hooks.delete_hook(hook_id)}
