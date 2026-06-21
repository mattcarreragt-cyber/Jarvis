"""Proxy des audios générés par ComfyUI (Kubuntu/RunPod) vers le dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from app.media import audio

router = APIRouter(prefix="/api/audio", tags=["audio"])

_MIME = {".flac": "audio/flac", ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg"}


@router.get("/view")
async def view(filename: str, subfolder: str = "", type: str = "output", src: str = ""):
    """Récupère un audio généré depuis ComfyUI et le renvoie (proxy, sans auth)."""
    data = await audio.fetch_audio(filename, subfolder, type, base_url=src or None)
    if data is None:
        raise HTTPException(502, "Audio indisponible (ComfyUI injoignable)")
    media_type = _MIME.get(Path(filename).suffix.lower(), "audio/flac")
    return Response(content=data, media_type=media_type)
