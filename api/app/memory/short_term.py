"""Mémoire court terme — Redis (voir docs/04_MEMORY.md).

Stocke les N derniers tours d'une session. Dégradation gracieuse : si Redis
est indisponible, on renvoie une mémoire vide plutôt que de planter le chat.
"""

from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from app.config import settings
from app.contracts import Turn

logger = logging.getLogger("jarvis.memory")

MAX_TURNS = 20
TTL_SECONDS = 60 * 60 * 24  # 24h


class ShortTermMemory:
    def __init__(self, url: str | None = None) -> None:
        self._url = url or settings.redis_url
        self._client: aioredis.Redis | None = None

    async def _conn(self) -> aioredis.Redis | None:
        if self._client is None:
            try:
                self._client = aioredis.from_url(
                    self._url, decode_responses=True, socket_timeout=2
                )
            except Exception as e:  # pragma: no cover
                logger.warning("Redis indisponible: %s", e)
                return None
        return self._client

    @staticmethod
    def _key(session_id: str) -> str:
        return f"session:{session_id}:turns"

    async def append(self, session_id: str, turn: Turn) -> None:
        client = await self._conn()
        if client is None:
            return
        try:
            key = self._key(session_id)
            await client.rpush(key, turn.model_dump_json())
            await client.ltrim(key, -MAX_TURNS, -1)
            await client.expire(key, TTL_SECONDS)
        except Exception as e:  # pragma: no cover
            logger.warning("append mémoire échoué: %s", e)

    async def recent(self, session_id: str, limit: int = MAX_TURNS) -> list[Turn]:
        client = await self._conn()
        if client is None:
            return []
        try:
            raw = await client.lrange(self._key(session_id), -limit, -1)
            return [Turn.model_validate(json.loads(r)) for r in raw]
        except Exception as e:  # pragma: no cover
            logger.warning("lecture mémoire échouée: %s", e)
            return []
