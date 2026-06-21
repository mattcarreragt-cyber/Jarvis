"""Endpoints agenda — tâches planifiées + notifications."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.automation import store

router = APIRouter(prefix="/api/agenda", tags=["agenda"])


@router.get("/tasks", dependencies=[Depends(require_api_key)])
async def list_tasks():
    return {"tasks": await store.list_tasks()}


@router.delete("/tasks/{task_id}", dependencies=[Depends(require_api_key)])
async def delete_task(task_id: str):
    return {"ok": await store.delete_task(task_id)}


@router.get("/notifications", dependencies=[Depends(require_api_key)])
async def notifications():
    return {
        "notifications": await store.list_notifications(),
        "unread": await store.unread_count(),
    }


@router.post("/notifications/read", dependencies=[Depends(require_api_key)])
async def mark_read():
    await store.mark_all_read()
    return {"ok": True}
