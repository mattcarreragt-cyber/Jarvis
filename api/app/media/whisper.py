"""Client STT — Faster-Whisper webservice (Kubuntu GPU).

Best-effort : Kubuntu éteint → transcribe() renvoie None.
Le réveil WoL est géré en amont par scheduler.dispatch("stt").

Service : onerahmet/openai-whisper-asr-webservice (endpoint POST /asr,
champ multipart `audio_file`).
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger("jarvis.whisper")


def _base(override: str | None = None) -> str:
    return (override or settings.whisper_base_url).rstrip("/")


async def health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{_base()}/docs")
            return r.status_code < 500
    except Exception:
        return False


async def transcribe(audio: bytes, filename: str = "audio.webm",
                     language: str = "fr", base_url: str | None = None,
                     timeout: float = 120) -> str | None:
    """Transcrit un fichier audio en texte. None si Whisper injoignable.

    base_url : surcharge l'endpoint (ex. Whisper CPU sur Unraid). None = défaut.
    timeout  : borne la tentative (plus court pour le palier local → fallback GPU
               rapide si le conteneur local est pendu).
    """
    if not audio:
        return None
    try:
        t = httpx.Timeout(timeout, connect=5)
        async with httpx.AsyncClient(timeout=t) as client:
            r = await client.post(
                f"{_base(base_url)}/asr",
                params={"task": "transcribe", "language": language, "output": "txt"},
                files={"audio_file": (filename, audio, "application/octet-stream")},
            )
            r.raise_for_status()
            return r.text.strip() or None
    except Exception as e:
        logger.debug("transcribe indisponible (Kubuntu éteint ?): %s", e)
        return None
