"""Tests génération audio — tokens, agent, routing (mocks)."""

from unittest.mock import AsyncMock, patch

from app.agents.audio_agent import AudioAgent
from app.contracts import AgentRequest, AgentStatus
from app.media import audio
from app.registry import registry
from app.router import route


def _req(msg="compose une musique électro de 20 secondes"):
    return AgentRequest(request_id="au1", session_id="s1", intent="audio", message=msg)


def test_build_audio_workflow_tokens():
    wf = audio.build_workflow("epic orchestral", "noise", 20, 7)
    assert wf is not None
    assert wf["2"]["inputs"]["text"] == "epic orchestral"   # __PROMPT__
    assert wf["3"]["inputs"]["text"] == "noise"             # __NEG__
    assert wf["4"]["inputs"]["seconds"] == 20               # __SECONDS__
    assert wf["5"]["inputs"]["seed"] == 7                   # seed injecté


def test_parse_duration_and_prompt():
    prompt, seconds = AudioAgent()._parse("compose une musique électro de 20 secondes")
    assert seconds == 20
    assert "électro" in prompt.lower()
    assert "musique" not in prompt.lower()


def test_parse_default_duration():
    _, seconds = AudioAgent()._parse("un jingle joyeux")
    assert seconds == audio.settings.audio_default_seconds


async def test_audio_gpu_unavailable():
    with patch("app.agents.audio_agent.dispatch",
               new=AsyncMock(return_value={"ok": False, "error": "WoL"})):
        resp = await AudioAgent().handle(_req())
    assert resp.status == AgentStatus.error
    assert "indisponible" in resp.content.lower()


async def test_audio_success_artifact():
    gen = {"filename": "jarvis_audio_001.flac", "subfolder": "", "type": "output", "seed": 9}
    with patch("app.agents.audio_agent.dispatch",
               new=AsyncMock(return_value={"ok": True, "base_url": None})), \
         patch("app.agents.audio_agent.audio.generate", new=AsyncMock(return_value=gen)), \
         patch("app.media.gallery.add_asset", new=AsyncMock(return_value="aid")):
        resp = await AudioAgent().handle(_req())
    assert resp.status == AgentStatus.ok
    assert resp.artifacts[0].kind == "audio"
    assert "/api/audio/view?" in resp.artifacts[0].url
    assert "jarvis_audio_001.flac" in resp.artifacts[0].url


async def test_audio_generation_failed():
    with patch("app.agents.audio_agent.dispatch",
               new=AsyncMock(return_value={"ok": True, "base_url": None})), \
         patch("app.agents.audio_agent.audio.generate", new=AsyncMock(return_value=None)):
        resp = await AudioAgent().handle(_req())
    assert resp.status == AgentStatus.error
    assert "Stable Audio" in resp.content


def test_router_audio_keywords():
    for p in ["compose une musique", "génère un jingle", "fais un bruitage de pluie"]:
        assert route(p, registry).agent == "audio", p
