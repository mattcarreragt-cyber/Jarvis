import asyncio
from enum import Enum

import asyncpg
import httpx
import redis.asyncio as aioredis
from qdrant_client import AsyncQdrantClient

from app.config import settings


class Status(str, Enum):
    ok = "ok"
    error = "error"
    unavailable = "unavailable"  # compute node offline (not an error)


async def _check_postgres() -> tuple[Status, str | None]:
    try:
        conn = await asyncpg.connect(
            settings.database_url.replace("+asyncpg", ""), timeout=3
        )
        await conn.execute("SELECT 1")
        await conn.close()
        return Status.ok, None
    except Exception as e:
        return Status.error, str(e)


async def _check_redis() -> tuple[Status, str | None]:
    try:
        client = aioredis.from_url(settings.redis_url, socket_timeout=3)
        await client.ping()
        await client.aclose()
        return Status.ok, None
    except Exception as e:
        return Status.error, str(e)


async def _check_qdrant() -> tuple[Status, str | None]:
    try:
        client = AsyncQdrantClient(url=settings.qdrant_url, timeout=3)
        await client.get_collections()
        await client.close()
        return Status.ok, None
    except Exception as e:
        return Status.error, str(e)


async def _check_http(url: str, path: str = "/") -> tuple[Status, str | None]:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{url.rstrip('/')}{path}")
            r.raise_for_status()
        return Status.ok, None
    except httpx.ConnectError:
        return Status.unavailable, "unreachable"
    except Exception as e:
        return Status.unavailable, str(e)


async def get_health() -> dict:
    # Core checks run in parallel — all must be ok
    pg, rd, qd = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_qdrant(),
    )

    # Compute checks — unavailable is not an error (Kubuntu may be sleeping)
    ollama, comfyui, whisper, piper = await asyncio.gather(
        _check_http(settings.ollama_base_url, "/api/tags"),
        _check_http(settings.comfyui_base_url, "/system_stats"),
        _check_http(settings.whisper_base_url, "/"),
        _check_http(settings.piper_base_url, "/"),
    )

    core_ok = all(s == Status.ok for s, _ in [pg, rd, qd])

    def _fmt(result: tuple[Status, str | None]) -> dict:
        status, detail = result
        return {"status": status, **({"detail": detail} if detail else {})}

    return {
        "status": "ok" if core_ok else "error",
        "core": {
            "postgres": _fmt(pg),
            "redis": _fmt(rd),
            "qdrant": _fmt(qd),
        },
        "compute": {
            "ollama": _fmt(ollama),
            "comfyui": _fmt(comfyui),
            "whisper": _fmt(whisper),
            "piper": _fmt(piper),
        },
    }
