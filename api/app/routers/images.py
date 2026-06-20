"""Proxy des images générées par ComfyUI (Kubuntu) vers le dashboard.

Pas d'auth : sert uniquement des images générées, consommé via <img src>.
L'API (Unraid, toujours allumée) relaie depuis Kubuntu qui peut dormir.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from app.media import comfyui

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/view")
async def view(filename: str, subfolder: str = "", type: str = "output"):
    """Récupère une image générée depuis ComfyUI et la renvoie au navigateur."""
    data = await comfyui.fetch_image(filename, subfolder, type)
    if data is None:
        raise HTTPException(502, "Image indisponible (ComfyUI/Kubuntu injoignable)")
    return Response(content=data, media_type="image/png")
