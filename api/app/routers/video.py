"""Endpoints vidéo — statut de job + proxy du fichier mp4 depuis ComfyUI (Kubuntu)."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import require_api_key
from app.media import video

router = APIRouter(prefix="/api/video", tags=["video"])


@router.get("/status/{job_id}", dependencies=[Depends(require_api_key)])
async def job_status(job_id: str):
    """État d'un job vidéo. Renvoie une view_url quand la vidéo est prête."""
    st = await video.status(job_id)
    if st.get("state") == "done" and st.get("media"):
        m = st["media"]
        st["view_url"] = "/api/video/view?" + urlencode({
            "filename": m["filename"], "subfolder": m["subfolder"], "type": m["type"],
        })
    return st


@router.get("/view")
async def view(filename: str, subfolder: str = "", type: str = "output"):
    """Récupère la vidéo générée depuis ComfyUI et la renvoie (proxy, sans auth)."""
    data = await video.fetch_video(filename, subfolder, type)
    if data is None:
        raise HTTPException(502, "Vidéo indisponible (ComfyUI/Kubuntu injoignable)")
    return Response(content=data, media_type="video/mp4")
