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
    from app.media import jobs
    job = jobs.get(job_id)
    base = job.base_url if job else None
    st = await video.status(job_id, base_url=base)
    if st.get("state") == "done" and st.get("media"):
        m = st["media"]
        params = {"filename": m["filename"], "subfolder": m["subfolder"], "type": m["type"]}
        if base:
            params["src"] = base          # le proxy /view saura où chercher
        st["view_url"] = "/api/video/view?" + urlencode(params)
    return st


@router.get("/view")
async def view(filename: str, subfolder: str = "", type: str = "output", src: str = ""):
    """Récupère la vidéo générée depuis ComfyUI et la renvoie (proxy, sans auth).

    src : endpoint ComfyUI d'origine (RunPod) ; vide = Kubuntu par défaut.
    """
    data = await video.fetch_video(filename, subfolder, type, base_url=src or None)
    if data is None:
        raise HTTPException(502, "Vidéo indisponible (ComfyUI injoignable)")
    return Response(content=data, media_type="video/mp4")
