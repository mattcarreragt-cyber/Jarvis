"""Endpoints galerie média — liste/suppression des images & vidéos générées."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.media import gallery

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("", dependencies=[Depends(require_api_key)])
async def list_media(kind: str | None = None):
    return {"assets": await gallery.list_assets(kind=kind)}


@router.delete("/{asset_id}", dependencies=[Depends(require_api_key)])
async def delete_media(asset_id: str):
    return {"ok": await gallery.delete_asset(asset_id)}
