"""Persistance agenda — tâches planifiées + notifications (Postgres).

Dégradation gracieuse : sans Postgres, tout renvoie vide / no-op.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.db import get_pool

logger = logging.getLogger("jarvis.agenda")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def compute_next_run(schedule_kind: str, time_of_day: str | None,
                     interval_sec: int | None, base: datetime | None = None) -> datetime:
    """Calcule le prochain déclenchement."""
    now = base or _now()
    if schedule_kind == "interval" and interval_sec:
        return now + timedelta(seconds=interval_sec)
    if schedule_kind == "daily" and time_of_day:
        hh, mm = (int(x) for x in time_of_day.split(":"))
        candidate = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    # once : géré par l'appelant (run_at fourni) ; fallback = maintenant
    return now


# ─── Tâches ──────────────────────────────────────────────────────────────────

async def add_task(label: str, kind: str, payload: str, schedule_kind: str,
                   next_run: datetime, time_of_day: str | None = None,
                   interval_sec: int | None = None) -> str | None:
    pool = await get_pool()
    if pool is None:
        return None
    tid = str(uuid.uuid4())
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO scheduled_tasks(id,label,kind,payload,schedule_kind,"
                "time_of_day,interval_sec,next_run) VALUES($1,$2,$3,$4,$5,$6,$7,$8)",
                tid, label, kind, payload, schedule_kind, time_of_day, interval_sec, next_run,
            )
        return tid
    except Exception as e:
        logger.warning("add_task: %s", e)
        return None


async def list_tasks(only_enabled: bool = False) -> list[dict]:
    pool = await get_pool()
    if pool is None:
        return []
    q = ("SELECT id,label,kind,payload,schedule_kind,time_of_day,interval_sec,"
         "next_run,enabled,last_run FROM scheduled_tasks")
    if only_enabled:
        q += " WHERE enabled = true"
    q += " ORDER BY next_run ASC"
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(q)
        return [dict(r) | {"next_run": r["next_run"].isoformat(),
                           "last_run": r["last_run"].isoformat() if r["last_run"] else None}
                for r in rows]
    except Exception as e:
        logger.warning("list_tasks: %s", e)
        return []


async def due_tasks() -> list[dict]:
    pool = await get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id,label,kind,payload,schedule_kind,time_of_day,interval_sec "
                "FROM scheduled_tasks WHERE enabled = true AND next_run <= $1", _now(),
            )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("due_tasks: %s", e)
        return []


async def mark_ran(task_id: str, schedule_kind: str, time_of_day: str | None,
                   interval_sec: int | None) -> None:
    """Met à jour last_run + next_run ; désactive les tâches 'once'."""
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            if schedule_kind == "once":
                await conn.execute(
                    "UPDATE scheduled_tasks SET enabled=false, last_run=$1 WHERE id=$2",
                    _now(), task_id)
            else:
                nxt = compute_next_run(schedule_kind, time_of_day, interval_sec)
                await conn.execute(
                    "UPDATE scheduled_tasks SET last_run=$1, next_run=$2 WHERE id=$3",
                    _now(), nxt, task_id)
    except Exception as e:
        logger.warning("mark_ran: %s", e)


async def delete_task(task_id: str) -> bool:
    pool = await get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            res = await conn.execute("DELETE FROM scheduled_tasks WHERE id=$1", task_id)
        return res.endswith("1")
    except Exception as e:
        logger.warning("delete_task: %s", e)
        return False


async def clear_tasks() -> int:
    pool = await get_pool()
    if pool is None:
        return 0
    try:
        async with pool.acquire() as conn:
            res = await conn.execute("DELETE FROM scheduled_tasks")
        return int(res.split()[-1]) if res.split()[-1].isdigit() else 0
    except Exception as e:
        logger.warning("clear_tasks: %s", e)
        return 0


# ─── Notifications ───────────────────────────────────────────────────────────

async def add_notification(text: str, source: str | None = None) -> None:
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO notifications(id,text,source) VALUES($1,$2,$3)",
                str(uuid.uuid4()), text, source)
    except Exception as e:
        logger.warning("add_notification: %s", e)


async def list_notifications(limit: int = 50) -> list[dict]:
    pool = await get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id,text,source,read,created_at FROM notifications "
                "ORDER BY created_at DESC LIMIT $1", limit)
        return [{"id": r["id"], "text": r["text"], "source": r["source"],
                 "read": r["read"], "created_at": r["created_at"].isoformat()} for r in rows]
    except Exception as e:
        logger.warning("list_notifications: %s", e)
        return []


async def unread_count() -> int:
    pool = await get_pool()
    if pool is None:
        return 0
    try:
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM notifications WHERE read=false") or 0
    except Exception as e:
        logger.warning("unread_count: %s", e)
        return 0


async def mark_all_read() -> None:
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE notifications SET read=true WHERE read=false")
    except Exception as e:
        logger.warning("mark_all_read: %s", e)
