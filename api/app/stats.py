"""Statistiques d'usage — agrégats sur les données déjà persistées.

Lecture seule sur Postgres (messages, routing_logs, tool_invocations, …).
Dégradation gracieuse : sans Postgres, tout renvoie des valeurs vides/zéro.
"""

from __future__ import annotations

import logging

from app.db import get_pool

logger = logging.getLogger("jarvis.stats")


async def _scalar(conn, q: str) -> int:
    try:
        return await conn.fetchval(q) or 0
    except Exception as e:
        logger.debug("scalar %s: %s", q[:40], e)
        return 0


async def get_stats() -> dict:
    pool = await get_pool()
    empty = {
        "totals": {"sessions": 0, "messages": 0, "facts": 0, "tasks": 0, "media": 0},
        "agent_usage": [], "method_breakdown": [], "messages_per_day": [],
        "tools": {"ok": 0, "error": 0, "top": []},
    }
    if pool is None:
        return empty

    out = {**empty}
    try:
        async with pool.acquire() as conn:
            out["totals"] = {
                "sessions": await _scalar(conn, "SELECT COUNT(*) FROM sessions"),
                "messages": await _scalar(conn, "SELECT COUNT(*) FROM messages"),
                "facts":    await _scalar(conn, "SELECT COUNT(*) FROM memory_facts"),
                "tasks":    await _scalar(conn, "SELECT COUNT(*) FROM scheduled_tasks"),
                "media":    await _scalar(conn, "SELECT COUNT(*) FROM media_assets"),
            }

            try:
                rows = await conn.fetch(
                    "SELECT agent, COUNT(*) AS n FROM routing_logs "
                    "GROUP BY agent ORDER BY n DESC LIMIT 12")
                out["agent_usage"] = [{"agent": r["agent"], "count": r["n"]} for r in rows]
            except Exception as e:
                logger.debug("agent_usage: %s", e)

            try:
                rows = await conn.fetch(
                    "SELECT method, COUNT(*) AS n FROM routing_logs GROUP BY method ORDER BY n DESC")
                out["method_breakdown"] = [{"method": r["method"], "count": r["n"]} for r in rows]
            except Exception as e:
                logger.debug("method_breakdown: %s", e)

            try:
                rows = await conn.fetch(
                    "SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS d, "
                    "COUNT(*) AS n FROM messages "
                    "WHERE created_at > now() - interval '7 days' "
                    "GROUP BY d ORDER BY d")
                out["messages_per_day"] = [{"day": r["d"], "count": r["n"]} for r in rows]
            except Exception as e:
                logger.debug("messages_per_day: %s", e)

            try:
                ok = await _scalar(conn, "SELECT COUNT(*) FROM tool_invocations WHERE result_ok = true")
                err = await _scalar(conn, "SELECT COUNT(*) FROM tool_invocations WHERE result_ok = false")
                top = await conn.fetch(
                    "SELECT tool, COUNT(*) AS n FROM tool_invocations "
                    "GROUP BY tool ORDER BY n DESC LIMIT 8")
                out["tools"] = {"ok": ok, "error": err,
                                "top": [{"tool": r["tool"], "count": r["n"]} for r in top]}
            except Exception as e:
                logger.debug("tools: %s", e)
    except Exception as e:
        logger.warning("get_stats: %s", e)
        return empty
    return out
