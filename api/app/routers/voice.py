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
    """Transcrit un enregistrement audio en texte (Whisper sur Kubuntu)."""
    disp = await dispatch("stt")          # réveille Kubuntu si besoin (GPU)
    if not disp.get("ok"):
        raise HTTPException(503, f"STT indisponible : {disp.get('error', 'GPU hors ligne')}")

    audio = await file.read()
    if len(audio) > MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(413, f"Audio trop volumineux (max {MAX_AUDIO_MB} Mo)")

    text = await whisper.transcribe(audio, filename=file.filename or "audio.webm",
                                    language=language)
    if text is None:
        raise HTTPException(502, "Transcription échouée (Whisper injoignable)")
    return {"text": text}


class SpeakRequest(BaseModel):
    text: str


@router.post("/speak", dependencies=[Depends(require_api_key)])
async def speak(req: SpeakRequest):
    """Synthèse vocale d'un texte (Piper, CPU Unraid). Renvoie un WAV."""
    await dispatch("tts")                 # machine=unraid, gpu=false → pas de WoL
    audio = await piper.synthesize(req.text)
    if audio is None:
        raise HTTPException(502, "Synthèse vocale indisponible (Piper non configuré)")
    return Response(content=audio, media_type="audio/wav")
