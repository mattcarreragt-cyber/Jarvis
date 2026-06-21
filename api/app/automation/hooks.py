"""Webhooks entrants — déclencheurs externes (Home Assistant, scripts…).

Chaque hook a un token secret et un message pré-configuré. Un appel HTTP sur
/api/hooks/{token} exécute ce message via le pipeline d'agents et notifie le
résultat. Permet de déclencher JARVIS depuis l'extérieur sans exposer l'API key.

Dégradation gracieuse : sans Postgres, tout renvoie vide / no-op.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone

from app.db import get_pool

logger = logging.getLogger("jarvis.hooks")


def new_token() -> str:
    return secrets.token_urlsafe(18)


async def create_hook(label: str, message: str) -> dict | None:
    pool = await get_pool()
    if pool is None:
        return None
    hid, token = str(uuid.uuid4()), new_token()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO webhooks(id,token,label,message) VALUES($1,$2,$3,$4)",
                hid, token, label, message)
        return {"id": hid, "token": token, "label": label, "message": message}
    except Exception as e:
        logger.warning("create_hook: %s", e)
        return None


async def list_hooks() -> list[dict]:
    pool = await get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id,token,label,message,enabled,run_count,last_triggered "
                "FROM webhooks ORDER BY created_at DESC")
        return [{"id": r["id"], "token": r["token"], "label": r["label"],
                 "message": r["message"], "enabled": r["enabled"],
                 "run_count": r["run_count"],
                 "last_triggered": r["last_triggered"].isoformat() if r["last_triggered"] else None}
                for r in rows]
    except Exception as e:
        logger.warning("list_hooks: %s", e)
        return []


async def get_by_token(token: str) -> dict | None:
    pool = await get_pool()
    if pool is None:
        return None
    try:
        async with pool.acquire() as conn:
            r = await conn.fetchrow(
                "SELECT id,label,message,enabled FROM webhooks WHERE token=$1", token)
        return dict(r) if r else None
    except Exception as e:
        logger.warning("get_by_token: %s", e)
        return None


async def mark_triggered(hook_id: str) -> None:
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE webhooks SET run_count=run_count+1, last_triggered=$1 WHERE id=$2",
                datetime.now(timezone.utc), hook_id)
    except Exception as e:
        logger.warning("mark_triggered: %s", e)


async def delete_hook(hook_id: str) -> bool:
    pool = await get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            res = await conn.execute("DELETE FROM webhooks WHERE id=$1", hook_id)
        return res.endswith("1")
    except Exception as e:
        logger.warning("delete_hook: %s", e)
        return False
