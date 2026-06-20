"""Ingestion de documents dans Qdrant — mode keyword (sans embeddings).

Stratégie :
- Vecteur dummy (taille 1, valeur 0.0) → sera remplacé par vrais embeddings
  quand Ollama/Kubuntu sera branché.
- Index full-text Qdrant sur le champ `text` → permet MatchText sans vecteurs.
- Chunking : fenêtre glissante 500 chars / overlap 80 chars.

Extraction multi-format : voir app/docs/extract.py
"""

from __future__ import annotations

import logging
import re
import uuid

from qdrant_client import AsyncQdrantClient, models

from app.config import settings
from app.docs.extract import extract_text
from app.llm.ollama import EMBED_DIM, embed_batch

logger = logging.getLogger("jarvis.docs")

COLLECTION = "docs"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
VECTOR_SIZE = EMBED_DIM   # 768 (nomic-embed-text) ; vecteur zéro si Ollama absent


def _qdrant() -> AsyncQdrantClient:
    return AsyncQdrantClient(url=settings.qdrant_url, timeout=5)


async def _ensure_collection(client: AsyncQdrantClient) -> None:
    existing = {c.name for c in (await client.get_collections()).collections}
    if COLLECTION not in existing:
        # Vecteurs nomic-embed-text (768d). En mode keyword pur, on stocke un
        # vecteur zéro ; la recherche full-text fonctionne indépendamment.
        await client.create_collection(
            COLLECTION,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE, distance=models.Distance.COSINE
            ),
        )
        # Index full-text sur le payload "text" pour MatchText
        await client.create_payload_index(
            COLLECTION,
            field_name="text",
            field_schema=models.TextIndexParams(
                type="text",
                tokenizer=models.TokenizerType.WORD,
                min_token_len=2,
                max_token_len=40,
                lowercase=True,
            ),
        )
        # Index sur "source" et "tags" pour filtrer par document
        await client.create_payload_index(
            COLLECTION,
            field_name="source",
            field_schema=models.KeywordIndexParams(type="keyword"),
        )
        logger.info("Collection '%s' créée avec index full-text", COLLECTION)


def _chunk(text: str) -> list[str]:
    """Fenêtre glissante simple."""
    text = re.sub(r"\s+", " ", text).strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 40]  # ignore les micro-chunks


async def delete_source(source: str) -> None:
    """Supprime tous les chunks d'une source (idempotent)."""
    client = _qdrant()
    try:
        await _ensure_collection(client)
        await client.delete(
            COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[
                    models.FieldCondition(key="source", match=models.MatchValue(value=source))
                ])
            ),
        )
    finally:
        await client.close()


async def ingest_file(
    filename: str,
    content: bytes,
    tags: list[str] | None = None,
    kind: str | None = None,
    source: str | None = None,
    replace: bool = False,
) -> dict:
    """Ingère un fichier, retourne {source, chunks_count}.

    source : identifiant logique du document (défaut = filename). La sync Nextcloud
             utilise "nextcloud:/chemin" pour distinguer la provenance.
    replace : si True, supprime d'abord les chunks existants de cette source
              (utilisé par la sync pour les fichiers modifiés).
    """
    from app.docs.extract import kind_for

    src = source or filename
    kind = kind or kind_for(filename)
    text = extract_text(filename, content)
    chunks = _chunk(text)
    if not chunks:
        raise ValueError("Document vide ou illisible")

    if replace:
        await delete_source(src)

    # Embeddings best-effort : vrais vecteurs si Ollama/Kubuntu dispo, sinon zéro.
    vectors = await embed_batch(chunks)
    zero = [0.0] * VECTOR_SIZE
    embedded_count = sum(1 for v in vectors if v is not None)

    client = _qdrant()
    try:
        await _ensure_collection(client)
        points = [
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors[i] if vectors[i] is not None else zero,
                payload={
                    "text":        chunk,
                    "source":      src,
                    "filename":    filename,
                    "chunk_index": i,
                    "kind":        kind,
                    "tags":        tags or [],
                    "embedded":    vectors[i] is not None,
                },
            )
            for i, chunk in enumerate(chunks)
        ]
        await client.upsert(COLLECTION, points=points)
        logger.info("Ingéré %s → %d chunks (%d embeddings)", src, len(chunks), embedded_count)
        return {"source": src, "chunks_count": len(chunks), "embedded": embedded_count}
    finally:
        await client.close()


async def list_sources() -> list[dict]:
    """Retourne la liste des documents ingérés avec leur nombre de chunks."""
    client = _qdrant()
    try:
        await _ensure_collection(client)
        # Scroll tous les points, on agrège par source
        sources: dict[str, int] = {}
        offset = None
        while True:
            result, offset = await client.scroll(
                COLLECTION, limit=100, offset=offset,
                with_payload=["source"], with_vectors=False,
            )
            for p in result:
                src = (p.payload or {}).get("source", "unknown")
                sources[src] = sources.get(src, 0) + 1
            if offset is None:
                break
        return [{"source": k, "chunks": v} for k, v in sorted(sources.items())]
    finally:
        await client.close()
