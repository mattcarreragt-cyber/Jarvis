"""Endpoints vidéo — statut de job + proxy du fichier mp4 depuis ComfyUI (Kubuntu)."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from app.auth import require_api_key
from app.config import settings
from app.media import jobs, video
from app.orchestration.scheduler import dispatch

router = APIRouter(prefix="/api/video", tags=["video"])

MAX_IMAGE_MB = 15


def _video_capability() -> str:
    use_hd = settings.runpod_enabled and bool(settings.runpod_comfyui_url)
    return "video.hd" if use_hd else "video"


@router.post("/animate", dependencies=[Depends(require_api_key)])
async def animate(file: UploadFile = File(...), seconds: int = Form(5)):
    """Anime une image existante (image→vidéo). Retourne un job_id à suivre."""
    capability = _video_capability()
    disp = await dispatch(capability)
    if not disp.get("ok"):
        raise HTTPException(503, f"GPU indisponible : {disp.get('error', 'hors ligne')}")

    image = await file.read()
    if len(image) > MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(413, f"Image trop volumineuse (max {MAX_IMAGE_MB} Mo)")

    base = disp.get("base_url")
    sub = await video.submit_img2vid(image, file.filename or "image.png", seconds, base_url=base)
    if not sub.get("ok"):
        raise HTTPException(502, sub.get("error", "Échec de l'animation"))

    job_id = sub["job_id"]
    jobs.register(job_id, kind="video", prompt=f"[image→vidéo] {file.filename}", base_url=base)
    return {"job_id": job_id, "seconds": sub["seconds"], "frames": sub["frames"]}


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
