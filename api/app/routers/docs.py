"""Endpoints ingestion et gestion des documents."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.auth import require_api_key
from app.docs.extract import SUPPORTED_EXT
from app.docs.ingest import ingest_file, list_sources

router = APIRouter(prefix="/api/docs", tags=["docs"])

ALLOWED_EXT = SUPPORTED_EXT
MAX_SIZE_MB = 50


@router.post("/ingest", dependencies=[Depends(require_api_key)])
async def ingest(
    file: UploadFile = File(...),
    tags: str = Form(default=""),          # CSV : "xenum,marketing,fiche-produit"
    kind: str = Form(default="doc"),       # "doc" | "fiche" | "brand" | ...
):
    """Upload et ingère un document (.txt, .md, .pdf) dans la base de connaissances."""
    from pathlib import Path
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Format non supporté : {ext}. Acceptés : {ALLOWED_EXT}")

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"Fichier trop volumineux (max {MAX_SIZE_MB} Mo)")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    try:
        result = await ingest_file(file.filename or "upload", content, tags=tag_list, kind=kind)
    except ValueError as e:
        raise HTTPException(422, str(e))

    return result


@router.get("/list", dependencies=[Depends(require_api_key)])
async def list_docs():
    """Liste les documents ingérés avec leur nombre de chunks."""
    return await list_sources()


@router.post("/reembed", dependencies=[Depends(require_api_key)])
async def reembed():
    """Ré-encode les chunks ingérés en mode keyword (embedded=false).

    À lancer une fois Kubuntu en ligne pour activer la recherche sémantique
    sur les documents ajoutés pendant que le GPU dormait.
    """
    from app.docs.reembed import reembed_pending
    return await reembed_pending()


@router.delete("/source", dependencies=[Depends(require_api_key)])
async def delete_source(source: str):
    """Supprime tous les chunks d'un document par son nom."""
    from qdrant_client import AsyncQdrantClient
    from qdrant_client import models as qm
    from app.config import settings
    client = AsyncQdrantClient(url=settings.qdrant_url, timeout=5)
    try:
        await client.delete(
            "docs",
            points_selector=qm.FilterSelector(
                filter=qm.Filter(must=[
                    qm.FieldCondition(key="source", match=qm.MatchValue(value=source))
                ])
            ),
        )
        return {"deleted": source}
    finally:
        await client.close()
