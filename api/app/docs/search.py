"""Recherche keyword dans Qdrant (mode sans embeddings).

Stratégie :
1. Tokeniser la query → mots significatifs (≥ 3 chars, hors stop words FR/EN).
2. Pour chaque token : MatchText dans Qdrant → récupère les chunks qui le contiennent.
3. Scorer chaque chunk par nombre de tokens matchés (union des résultats).
4. Retourner top-k triés par score décroissant.

Quand Ollama sera branché (Kubuntu) : on remplacera par une vraie recherche
vectorielle cosine + re-ranking, mais l'interface reste identique.
"""

from __future__ import annotations

import logging
import re

from qdrant_client import AsyncQdrantClient, models

from app.config import settings
from app.docs.ingest import COLLECTION, _ensure_collection

logger = logging.getLogger("jarvis.search")

# Stop words FR + EN minimalistes
_STOP = {
    "le", "la", "les", "de", "du", "des", "un", "une", "en", "et", "ou",
    "est", "are", "the", "of", "in", "to", "a", "is", "for", "que", "qui",
    "il", "elle", "on", "nous", "vous", "ils", "elles", "ce", "se", "sa",
    "son", "sur", "par", "avec", "dans", "plus", "pas", "ne", "je", "tu",
    "me", "ma", "mon", "mes", "ses", "leur", "leurs", "this", "that",
}


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-zA-ZÀ-ÿ]{3,}", text.lower())
    return [w for w in words if w not in _STOP]


async def keyword_search(
    query: str,
    top_k: int = 5,
    source_filter: str | None = None,
    tags_filter: list[str] | None = None,
) -> list[dict]:
    """
    Retourne top-k chunks pertinents sous la forme :
    [{"text": ..., "source": ..., "score": ..., "tags": ...}]
    """
    tokens = _tokens(query)
    if not tokens:
        return []

    client = AsyncQdrantClient(url=settings.qdrant_url, timeout=5)
    try:
        await _ensure_collection(client)
        scores: dict[str, dict] = {}   # point_id → {payload, score}

        for token in tokens:
            must: list = [
                models.FieldCondition(
                    key="text", match=models.MatchText(text=token)
                )
            ]
            if source_filter:
                must.append(models.FieldCondition(
                    key="source",
                    match=models.MatchValue(value=source_filter),
                ))
            if tags_filter:
                must.append(models.FieldCondition(
                    key="tags",
                    match=models.MatchAny(any=tags_filter),
                ))

            results, _ = await client.scroll(
                COLLECTION,
                scroll_filter=models.Filter(must=must),
                limit=20,
                with_payload=True,
                with_vectors=False,
            )
            for point in results:
                pid = str(point.id)
                if pid not in scores:
                    scores[pid] = {"payload": point.payload or {}, "score": 0}
                scores[pid]["score"] += 1

        ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return [
            {
                "text":   r["payload"].get("text", ""),
                "source": r["payload"].get("source", ""),
                "tags":   r["payload"].get("tags", []),
                "score":  r["score"],
            }
            for r in ranked[:top_k]
        ]

    except Exception as e:
        logger.warning("keyword_search échouée: %s", e)
        return []
    finally:
        await client.close()
