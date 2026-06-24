"""Serveur HTTP Piper (TTS) — CPU, Unraid.

API compatible avec le client app/media/piper.py :
  - POST /          {"text": "...", "voice": "fr_FR-siwis-medium"}  -> audio/wav
  - GET  /?text=... &voice=...                                       -> audio/wav
  - GET  /health                                                     -> {"ok": true}

Les voix sont téléchargées automatiquement depuis Hugging Face (rhasspy/piper-voices)
au premier usage et mises en cache dans PIPER_DATA_DIR. Le choix de voix se fait
par requête (paramètre `voice`), avec repli sur PIPER_DEFAULT_VOICE.
"""

from __future__ import annotations

import asyncio
import os
import tempfile

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

DATA_DIR = os.getenv("PIPER_DATA_DIR", "/data")
DEFAULT_VOICE = os.getenv("PIPER_DEFAULT_VOICE", "fr_FR-siwis-medium")

app = FastAPI(title="Piper TTS")

# Sérialise les synthèses : Piper charge le modèle en mémoire, on évite la
# contention CPU en n'en lançant qu'une à la fois.
_lock = asyncio.Lock()


def _voice_present(voice: str) -> bool:
    return os.path.exists(os.path.join(DATA_DIR, f"{voice}.onnx"))


async def _ensure_voice(voice: str) -> None:
    """Télécharge la voix dans DATA_DIR si absente (piper-tts ≥1.x)."""
    if _voice_present(voice):
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        "python", "-m", "piper.download_voices", voice,
        cwd=DATA_DIR,                       # télécharge dans le cache monté
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0 or not _voice_present(voice):
        raise RuntimeError(
            f"téléchargement de la voix {voice} échoué : "
            + stderr.decode("utf-8", "replace")[:400]
        )


async def _synthesize(text: str, voice: str) -> bytes:
    text = (text or "").strip()
    if not text:
        return b""
    voice = voice or DEFAULT_VOICE
    await _ensure_voice(voice)
    out_path = tempfile.mktemp(suffix=".wav", dir="/tmp")
    async with _lock:
        proc = await asyncio.create_subprocess_exec(
            "python", "-m", "piper",
            "--model", voice,
            "--data-dir", DATA_DIR,
            "--output_file", out_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate(text.encode("utf-8"))
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", "replace")[:500] or "piper a échoué")
    try:
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


@app.get("/health")
async def health():
    return {"ok": True, "default_voice": DEFAULT_VOICE}


@app.post("/")
async def post_tts(req: Request):
    body = await req.json()
    wav = await _synthesize(body.get("text", ""), body.get("voice", ""))
    if not wav:
        return JSONResponse({"error": "texte vide"}, status_code=400)
    return Response(content=wav, media_type="audio/wav")


@app.get("/")
async def get_tts(text: str = "", voice: str = ""):
    # Sert aussi de sonde santé : GET / sans texte -> 200 rapide.
    if not text:
        return JSONResponse({"ok": True})
    wav = await _synthesize(text, voice)
    return Response(content=wav, media_type="audio/wav")
