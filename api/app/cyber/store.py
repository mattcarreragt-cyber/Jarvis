"""Persistance cyber — inventaire d'hôtes + findings (Postgres). No-op sans DB."""

from __future__ import annotations

import logging
import uuid

from app.db import get_pool

logger = logging.getLogger("jarvis.cyber.store")


async def add_host(label: str, hostname: str, username: str, port: int = 22) -> dict | None:
    pool = await get_pool()
    if pool is None:
        return None
    hid = str(uuid.uuid4())
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO cyber_hosts(id,label,hostname,port,username) VALUES($1,$2,$3,$4,$5)",
                hid, label, hostname, port, username)
        return {"id": hid, "label": label, "hostname": hostname, "port": port, "username": username}
    except Exception as e:
        logger.warning("add_host: %s", e)
        return None


async def list_hosts() -> list[dict]:
    pool = await get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id,label,hostname,port,username FROM cyber_hosts ORDER BY label")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("list_hosts: %s", e)
        return []


async def get_host(id_or_label: str) -> dict | None:
    pool = await get_pool()
    if pool is None:
        return None
    try:
        async with pool.acquire() as conn:
            r = await conn.fetchrow(
                "SELECT id,label,hostname,port,username FROM cyber_hosts "
                "WHERE id=$1 OR lower(label)=lower($1)", id_or_label)
        return dict(r) if r else None
    except Exception as e:
        logger.warning("get_host: %s", e)
        return None


async def delete_host(host_id: str) -> bool:
    pool = await get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            res = await conn.execute("DELETE FROM cyber_hosts WHERE id=$1", host_id)
        return res.endswith("1")
    except Exception as e:
        logger.warning("delete_host: %s", e)
        return False


async def save_findings(host_id: str, findings: list[dict]) -> None:
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM cyber_findings WHERE host_id=$1", host_id)
                for f in findings:
                    await conn.execute(
                        "INSERT INTO cyber_findings(id,host_id,check,severity,title,detail,"
                        "recommendation,remediation) VALUES($1,$2,$3,$4,$5,$6,$7,$8)",
                        str(uuid.uuid4()), host_id, f["check"], f["severity"], f["title"],
                        f.get("detail"), f.get("recommendation"), f.get("remediation"))
    except Exception as e:
        logger.warning("save_findings: %s", e)


async def save_score(host_id: str, score: int, grade: str) -> None:
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO cyber_scores(id,host_id,score,grade) VALUES($1,$2,$3,$4)",
                str(uuid.uuid4()), host_id, score, grade)
    except Exception as e:
        logger.warning("save_score: %s", e)


async def score_history(host_id: str, limit: int = 30) -> list[dict]:
    pool = await get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT score,grade,created_at FROM cyber_scores WHERE host_id=$1 "
                "ORDER BY created_at DESC LIMIT $2", host_id, limit)
        return [{"score": r["score"], "grade": r["grade"],
                 "created_at": r["created_at"].isoformat()} for r in reversed(rows)]
    except Exception as e:
        logger.warning("score_history: %s", e)
        return []


async def latest_findings(host_id: str) -> list[dict]:
    pool = await get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT check,severity,title,detail,recommendation,remediation "
                "FROM cyber_findings WHERE host_id=$1 ORDER BY created_at DESC", host_id)
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("latest_findings: %s", e)
        return []
