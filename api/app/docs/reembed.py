"""Ré-embedding des chunks ingérés en mode keyword (vecteur zéro).

Quand Kubuntu était éteint à l'ingestion, les chunks ont un vecteur zéro et
`embedded: false`. Cette passe les ré-encode avec nomic-embed-text dès que
Kubuntu est en ligne, activant la recherche sémantique sur tout le corpus.

Best-effort : si Ollama est injoignable, on s'arrête proprement.
"""

from __future__ import annotations

import logging

from qdrant_client import AsyncQdrantClient, models

from app.config import settings
from app.docs.ingest import COLLECTION, _ensure_collection
from app.llm.ollama import embed, health

logger = logging.getLogger("jarvis.reembed")


async def reembed_pending(batch: int = 64) -> dict:
    """Ré-encode les chunks embedded=false. Retourne un récap."""
    if not await health():
        return {"ok": False, "error": "Ollama injoignable (Kubuntu éteint ?)"}

    client = AsyncQdrantClient(url=settings.qdrant_url, timeout=10)
    result = {"ok": True, "updated": 0, "remaining": 0, "errors": 0}
    try:
        await _ensure_collection(client)
        flt = models.Filter(must=[
            models.FieldCondition(key="embedded", match=models.MatchValue(value=False)),
        ])
        offset = None
        while True:
            points, offset = await client.scroll(
                COLLECTION, scroll_filter=flt, limit=batch, offset=offset,
                with_payload=True, with_vectors=False,
            )
            if not points:
                break

            updates: list[models.PointStruct] = []
            for p in points:
                text = (p.payload or {}).get("text", "")
                vector = await embed(text)
                if vector is None:
                    # Ollama est retombé → on arrête, le reste sera repris plus tard
                    result["remaining"] = await _count_pending(client, flt)
                    result["ok"] = False
                    result["error"] = "Ollama coupé en cours de route"
                    if updates:
                        await _apply(client, updates)
                        result["updated"] += len(updates)
                    return result
                new_payload = {**(p.payload or {}), "embedded": True}
                updates.append(models.PointStruct(id=p.id, vector=vector, payload=new_payload))

            await _apply(client, updates)
            result["updated"] += len(updates)
            if offset is None:
                break

        logger.info("Ré-embedding terminé : %d chunks mis à jour", result["updated"])
        return result
    except Exception as e:
        logger.warning("reembed_pending: %s", e)
        return {"ok": False, "error": str(e), "updated": result["updated"]}
    finally:
        await client.close()


async def _apply(client: AsyncQdrantClient, points: list[models.PointStruct]) -> None:
    if points:
        await client.upsert(COLLECTION, points=points)


async def _count_pending(client: AsyncQdrantClient, flt: models.Filter) -> int:
    try:
        res = await client.count(COLLECTION, count_filter=flt, exact=True)
        return res.count
    except Exception:
        return -1
