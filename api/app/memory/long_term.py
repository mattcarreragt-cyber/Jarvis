"""Mémoire long terme sémantique — Qdrant + embeddings Ollama.

Voir docs/04_MEMORY.md. Embeddings générés localement (local-first).
Dégradation gracieuse : si Qdrant ou Ollama est indisponible, le rappel
renvoie une liste vide et l'écriture est ignorée silencieusement.
"""

from __future__ import annotations

import logging
import uuid

import httpx
from qdrant_client import AsyncQdrantClient, models

from app.config import settings

logger = logging.getLogger("jarvis.memory")

COLLECTION = "memory"
EMBED_MODEL = "nomic-embed-text"
VECTOR_SIZE = 768  # dimension de nomic-embed-text


class LongTermMemory:
    def __init__(self, qdrant_url: str | None = None, ollama_url: str | None = None) -> None:
        self._qdrant_url = qdrant_url or settings.qdrant_url
        self._ollama_url = ollama_url or settings.ollama_base_url
        self._client: AsyncQdrantClient | None = None

    def _qdrant(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = AsyncQdrantClient(url=self._qdrant_url, timeout=3)
        return self._client

    async def ensure_collection(self) -> bool:
        try:
            client = self._qdrant()
            existing = {c.name for c in (await client.get_collections()).collections}
            if COLLECTION not in existing:
                await client.create_collection(
                    COLLECTION,
                    vectors_config=models.VectorParams(
                        size=VECTOR_SIZE, distance=models.Distance.COSINE
                    ),
                )
            return True
        except Exception as e:  # pragma: no cover
            logger.warning("Qdrant indisponible: %s", e)
            return False

    async def _embed(self, text: str) -> list[float] | None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{self._ollama_url.rstrip('/')}/api/embeddings",
                    json={"model": EMBED_MODEL, "prompt": text},
                )
                r.raise_for_status()
                return r.json()["embedding"]
        except Exception as e:  # pragma: no cover
            logger.warning("Embedding indisponible (Kubuntu éteint ?): %s", e)
            return None

    async def remember(
        self, text: str, kind: str = "fact", session_id: str | None = None
    ) -> bool:
        vector = await self._embed(text)
        if vector is None or not await self.ensure_collection():
            return False
        try:
            await self._qdrant().upsert(
                COLLECTION,
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={"text": text, "kind": kind, "session_id": session_id},
                    )
                ],
            )
            return True
        except Exception as e:  # pragma: no cover
            logger.warning("écriture mémoire long terme échouée: %s", e)
            return False

    async def recall(self, query: str, top_k: int = 3) -> list[str]:
        vector = await self._embed(query)
        if vector is None:
            return []
        try:
            hits = await self._qdrant().search(
                COLLECTION, query_vector=vector, limit=top_k
            )
            return [h.payload.get("text", "") for h in hits if h.payload]
        except Exception as e:  # pragma: no cover
            logger.warning("rappel mémoire échoué: %s", e)
            return []
