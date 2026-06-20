"""Tests voix — clients STT/TTS + endpoints (mocks, sans services live)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as m
from app.media import piper, whisper

client = TestClient(m.app)


# ─── Clients (dégradation gracieuse) ─────────────────────────────────────────

async def test_whisper_empty_audio():
    assert await whisper.transcribe(b"") is None


async def test_piper_empty_text():
    assert await piper.synthesize("") is None


# ─── Endpoint /transcribe ────────────────────────────────────────────────────

def test_transcribe_ok():
    with patch("app.routers.voice.dispatch",
               new=AsyncMock(return_value={"ok": True, "model": "large-v3"})), \
         patch("app.routers.voice.whisper.transcribe",
               new=AsyncMock(return_value="bonjour jarvis")):
        r = client.post("/api/voice/transcribe",
                        files={"file": ("a.webm", b"fakeaudio", "audio/webm")})
    assert r.status_code == 200
    assert r.json()["text"] == "bonjour jarvis"


def test_transcribe_gpu_down():
    with patch("app.routers.voice.dispatch",
               new=AsyncMock(return_value={"ok": False, "error": "WoL échoué"})):
        r = client.post("/api/voice/transcribe",
                        files={"file": ("a.webm", b"fakeaudio", "audio/webm")})
    assert r.status_code == 503


def test_transcribe_whisper_unreachable():
    with patch("app.routers.voice.dispatch",
               new=AsyncMock(return_value={"ok": True, "model": "large-v3"})), \
         patch("app.routers.voice.whisper.transcribe", new=AsyncMock(return_value=None)):
        r = client.post("/api/voice/transcribe",
                        files={"file": ("a.webm", b"fakeaudio", "audio/webm")})
    assert r.status_code == 502


# ─── Endpoint /speak ─────────────────────────────────────────────────────────

def test_speak_ok():
    with patch("app.routers.voice.dispatch", new=AsyncMock(return_value={"ok": True})), \
         patch("app.routers.voice.piper.synthesize", new=AsyncMock(return_value=b"RIFFwav")):
        r = client.post("/api/voice/speak", json={"text": "salut"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.content == b"RIFFwav"


def test_speak_unavailable():
    with patch("app.routers.voice.dispatch", new=AsyncMock(return_value={"ok": True})), \
         patch("app.routers.voice.piper.synthesize", new=AsyncMock(return_value=None)):
        r = client.post("/api/voice/speak", json={"text": "salut"})
    assert r.status_code == 502
