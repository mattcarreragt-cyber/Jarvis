"""Persistance async Postgres — messages et audit (routing_logs, tool_invocations).

Dégradation gracieuse : si Postgres est absent, on log un warning et on continue.
Les migrations doivent être appliquées avant le démarrage (alembic upgrade head).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

import asyncpg

from app.config import settings
from app.contracts import AgentResponse, RouteDecision

logger = logging.getLogger("jarvis.db")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool | None:
    global _pool
    if _pool is None:
        try:
            url = settings.database_url.replace("+asyncpg", "")
            _pool = await asyncpg.create_pool(url, min_size=1, max_size=5, timeout=3)
        except Exception as e:
            logger.warning("Postgres indisponible: %s", e)
    return _pool


async def ensure_session(session_id: str) -> None:
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO sessions(id) VALUES($1) ON CONFLICT(id) DO NOTHING",
                session_id,
            )
    except Exception as e:
        logger.warning("ensure_session: %s", e)


async def persist_message(
    session_id: str, role: str, content: str, agent: str | None = None
) -> None:
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO messages(id, session_id, role, content, agent) "
                "VALUES($1,$2,$3,$4,$5)",
                str(uuid.uuid4()), session_id, role, content, agent,
            )
    except Exception as e:
        logger.warning("persist_message: %s", e)


async def persist_routing_log(
    request_id: str, session_id: str, decision: RouteDecision
) -> None:
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO routing_logs(id, request_id, session_id, agent, method, score) "
                "VALUES($1,$2,$3,$4,$5,$6)",
                str(uuid.uuid4()), request_id, session_id,
                decision.agent, decision.method, decision.score,
            )
    except Exception as e:
        logger.warning("persist_routing_log: %s", e)


async def persist_tool_invocations(
    request_id: str, response: AgentResponse
) -> None:
    pool = await get_pool()
    if pool is None or not response.tool_calls:
        return
    try:
        async with pool.acquire() as conn:
            await conn.executemany(
                "INSERT INTO tool_invocations(id, request_id, tool, args, result_ok, error) "
                "VALUES($1,$2,$3,$4,$5,$6)",
                [
                    (
                        str(uuid.uuid4()), request_id, tc.tool,
                        str(tc.args),
                        tc.result.ok if tc.result else False,
                        tc.result.error if tc.result else None,
                    )
                    for tc in response.tool_calls
                ],
            )
    except Exception as e:
        logger.warning("persist_tool_invocations: %s", e)
