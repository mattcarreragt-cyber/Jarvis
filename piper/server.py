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
# Sérialise les téléchargements de voix (indépendant des synthèses en cours).
_download_lock = asyncio.Lock()


def _voice_present(voice: str) -> bool:
    return os.path.exists(os.path.join(DATA_DIR, f"{voice}.onnx"))


async def _ensure_voice(voice: str) -> None:
    """Télécharge la voix dans DATA_DIR si absente (piper-tts ≥1.x).

    Téléchargement dans un répertoire temporaire puis déplacement atomique :
    un download interrompu (restart conteneur, requêtes concurrentes) ne peut
    pas laisser un .onnx tronqué que piper considérerait valide pour toujours.
    """
    if _voice_present(voice):
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    async with _download_lock:
        if _voice_present(voice):           # une requête concurrente l'a déjà fait
            return
        with tempfile.TemporaryDirectory(dir=DATA_DIR) as tmp:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "piper.download_voices", voice,
                cwd=tmp,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            onnx = os.path.join(tmp, f"{voice}.onnx")
            if proc.returncode != 0 or not os.path.exists(onnx):
                raise RuntimeError(
                    f"téléchargement de la voix {voice} échoué : "
                    + stderr.decode("utf-8", "replace")[:400]
                )
            # Déplacement atomique (même filesystem : tmp est dans DATA_DIR)
            for suffix in (".onnx.json", ".onnx"):
                src = os.path.join(tmp, f"{voice}{suffix}")
                if os.path.exists(src):
                    os.replace(src, os.path.join(DATA_DIR, f"{voice}{suffix}"))


# Modèles chargés en mémoire (voix → PiperVoice). Garder le modèle chaud
# évite de payer le chargement ONNX (~1-3 s CPU) à chaque phrase.
_loaded: dict[str, object] = {}
_MAX_LOADED = 2  # ~60-100 Mo par voix — on garde les 2 dernières utilisées


def _get_voice(voice: str):
    from piper import PiperVoice
    v = _loaded.pop(voice, None)          # pop+réinsertion = ordre LRU
    if v is None:
        v = PiperVoice.load(os.path.join(DATA_DIR, f"{voice}.onnx"))
    _loaded[voice] = v
    while len(_loaded) > _MAX_LOADED:
        _loaded.pop(next(iter(_loaded)))  # évince la moins récemment utilisée
    return v


def _synth_blocking(voice_name: str, text: str) -> bytes:
    """Synthèse synchrone (exécutée dans un thread executor)."""
    import io
    import wave

    v = _get_voice(voice_name)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        v.synthesize_wav(text, wf)
    return buf.getvalue()


async def _synthesize(text: str, voice: str) -> bytes:
    text = (text or "").strip()
    if not text:
        return b""
    voice = voice or DEFAULT_VOICE
    await _ensure_voice(voice)
    async with _lock:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _synth_blocking, voice, text)


@app.on_event("startup")
async def _warmup():
    """Précharge la voix par défaut (best-effort) : la première réponse
    vocale n'attend ni téléchargement ni chargement du modèle."""
    try:
        await _ensure_voice(DEFAULT_VOICE)
        await asyncio.get_running_loop().run_in_executor(None, _get_voice, DEFAULT_VOICE)
    except Exception:
        pass  # pas de réseau au démarrage → la voix se chargera à la 1re requête


@app.get("/health")
async def health():
    return {"ok": True, "default_voice": DEFAULT_VOICE, "loaded": list(_loaded)}


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
