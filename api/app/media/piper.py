"""Client TTS — Piper (Unraid, CPU). Pas de GPU, ne réveille jamais Kubuntu.

Best-effort : serveur Piper injoignable → synthesize() renvoie None (le dashboard
n'émet alors pas de son, sans erreur bloquante).

Cible un serveur HTTP Piper (voir UNRAID_SETUP.md). On tente l'API JSON, avec
repli sur le paramètre de requête `?text=` selon l'implémentation.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger("jarvis.piper")


def _base() -> str:
    return settings.piper_base_url.rstrip("/")


async def synthesize(text: str, voice: str | None = None) -> bytes | None:
    """Synthèse vocale d'un texte → octets WAV. None si indisponible.

    voice : nom de la voix Piper (ex. fr_FR-siwis-medium). None = défaut serveur/config.
    """
    text = (text or "").strip()
    if not text:
        return None
    voice = voice or settings.piper_voice

    base = _base()
    async with httpx.AsyncClient(timeout=60) as client:
        # 1) POST JSON {"text": ..., "voice": ...}
        try:
            r = await client.post(base, json={"text": text, "voice": voice})
            if r.status_code < 400 and r.content:
                return r.content
        except Exception:
            pass
        # 2) Repli : GET ?text=...&voice=...
        try:
            r = await client.get(base, params={"text": text, "voice": voice})
            if r.status_code < 400 and r.content:
                return r.content
        except Exception as e:
            logger.debug("synthesize indisponible: %s", e)
    return None


async def health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(_base())
            return r.status_code < 500
    except Exception:
        return False
