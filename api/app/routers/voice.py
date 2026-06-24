"""Endpoints voix — STT (Whisper/Kubuntu) et TTS (Piper/Unraid)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth import require_api_key
from app.media import piper, whisper
from app.orchestration.scheduler import dispatch

router = APIRouter(prefix="/api/voice", tags=["voice"])

MAX_AUDIO_MB = 25


@router.post("/transcribe", dependencies=[Depends(require_api_key)])
async def transcribe(file: UploadFile = File(...), language: str = "fr"):
    """Transcrit un enregistrement audio en texte.

    Essaie d'abord Whisper CPU sur Unraid (stt.local, sans réveiller Kubuntu),
    puis retombe sur Whisper GPU Kubuntu (stt) si le local échoue.
    """
    from app.config import settings

    audio = await file.read()
    if len(audio) > MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(413, f"Audio trop volumineux (max {MAX_AUDIO_MB} Mo)")
    fname = file.filename or "audio.webm"

    # 1) Local CPU Unraid (pas de WoL)
    if settings.local_cpu_enabled:
        local = await dispatch("stt.local")
        if local.get("ok"):
            text = await whisper.transcribe(audio, filename=fname, language=language,
                                            base_url=local.get("base_url"))
            if text is not None:
                return {"text": text, "source": "unraid-cpu"}

    # 2) Fallback Whisper GPU Kubuntu (réveille Kubuntu si besoin)
    disp = await dispatch("stt")
    if not disp.get("ok"):
        raise HTTPException(503, f"STT indisponible : {disp.get('error', 'GPU hors ligne')}")
    text = await whisper.transcribe(audio, filename=fname, language=language,
                                    base_url=disp.get("base_url"))
    if text is None:
        raise HTTPException(502, "Transcription échouée (Whisper injoignable)")
    return {"text": text, "source": "kubuntu-gpu"}


class SpeakRequest(BaseModel):
    text: str
    voice: str | None = None   # ex. fr_FR-siwis-medium ; None = voix par défaut


@router.post("/speak", dependencies=[Depends(require_api_key)])
async def speak(req: SpeakRequest):
    """Synthèse vocale d'un texte (Piper, CPU Unraid). Renvoie un WAV."""
    await dispatch("tts")                 # machine=unraid, gpu=false → pas de WoL
    audio = await piper.synthesize(req.text, voice=req.voice)
    if audio is None:
        raise HTTPException(502, "Synthèse vocale indisponible (Piper non configuré)")
    return Response(content=audio, media_type="audio/wav")


# Voix françaises Piper proposées dans le dashboard (téléchargées à la demande).
VOICES = [
    {"id": "fr_FR-siwis-medium", "label": "Siwis (femme, claire)"},
    {"id": "fr_FR-tom-medium",   "label": "Tom (homme)"},
    {"id": "fr_FR-upmc-medium",  "label": "UPMC (femme)"},
    {"id": "fr_FR-gilles-low",   "label": "Gilles (homme, rapide)"},
    {"id": "fr_FR-mls-medium",   "label": "MLS (multi-locuteurs)"},
]


@router.get("/voices")
async def voices():
    """Liste des voix disponibles + voix par défaut (pour le sélecteur dashboard)."""
    from app.config import settings
    return {"voices": VOICES, "default": settings.piper_voice}
