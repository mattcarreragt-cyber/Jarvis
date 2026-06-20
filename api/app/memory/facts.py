"""Faits mémorisés durables — Postgres (table memory_facts).

Toujours disponible (pas besoin d'Ollama). Complète la mémoire sémantique Qdrant :
- ici : stockage durable + recherche keyword (ILIKE), survit aux redémarrages ;
- Qdrant/long_term : rappel sémantique quand les embeddings sont dispo.

Dégradation gracieuse : sans Postgres, tout renvoie vide / no-op.
"""

from __future__ import annotations

import logging
import re
import uuid

from app.db import get_pool

logger = logging.getLogger("jarvis.facts")

_STOP = {
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "que", "qui",
    "je", "tu", "il", "elle", "mon", "ma", "mes", "ton", "ta", "est", "sur",
    "pour", "dans", "the", "a", "of", "to", "is", "my", "que",
}


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-zA-ZÀ-ÿ]{3,}", text.lower()) if w not in _STOP]


async def add_fact(text: str, kind: str = "fact", session_id: str | None = None) -> bool:
    text = (text or "").strip()
    if not text:
        return False
    pool = await get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO memory_facts(id, text, kind, session_id) VALUES($1,$2,$3,$4)",
                str(uuid.uuid4()), text, kind, session_id,
            )
        return True
    except Exception as e:
        logger.warning("add_fact: %s", e)
        return False


async def list_facts(limit: int = 100) -> list[dict]:
    pool = await get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, text, kind, created_at FROM memory_facts "
                "ORDER BY created_at DESC LIMIT $1", limit,
            )
        return [{"id": r["id"], "text": r["text"], "kind": r["kind"],
                 "created_at": r["created_at"].isoformat()} for r in rows]
    except Exception as e:
        logger.warning("list_facts: %s", e)
        return []


async def search_facts(query: str, limit: int = 5) -> list[str]:
    """Recherche keyword (ILIKE) ; repli sur les plus récents si aucun token."""
    pool = await get_pool()
    if pool is None:
        return []
    tokens = _tokens(query)
    try:
        async with pool.acquire() as conn:
            if tokens:
                clauses = " OR ".join(f"text ILIKE ${i+2}" for i in range(len(tokens)))
                args = [limit] + [f"%{t}%" for t in tokens]
                rows = await conn.fetch(
                    f"SELECT text FROM memory_facts WHERE {clauses} "
                    f"ORDER BY created_at DESC LIMIT $1", *args,
                )
                if rows:
                    return [r["text"] for r in rows]
            # Repli : faits récents (profil utilisateur, préférences…)
            rows = await conn.fetch(
                "SELECT text FROM memory_facts ORDER BY created_at DESC LIMIT $1", limit,
            )
        return [r["text"] for r in rows]
    except Exception as e:
        logger.warning("search_facts: %s", e)
        return []


async def delete_fact(fact_id: str) -> bool:
    pool = await get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            res = await conn.execute("DELETE FROM memory_facts WHERE id=$1", fact_id)
        return res.endswith("1")
    except Exception as e:
        logger.warning("delete_fact: %s", e)
        return False


async def clear_facts() -> int:
    pool = await get_pool()
    if pool is None:
        return 0
    try:
        async with pool.acquire() as conn:
            res = await conn.execute("DELETE FROM memory_facts")
        return int(res.split()[-1]) if res.split()[-1].isdigit() else 0
    except Exception as e:
        logger.warning("clear_facts: %s", e)
        return 0
