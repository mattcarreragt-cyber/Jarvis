"""Tests Agent Vidéo + client (template tokens, dispatch, mocks)."""

from unittest.mock import AsyncMock, patch

from app.agents.video_agent import VideoAgent
from app.contracts import AgentRequest, AgentStatus
from app.media import video
from app.registry import registry
from app.router import route


def _req(message="génère une vidéo de 15 secondes d'un moteur Xenum"):
    return AgentRequest(request_id="v1", session_id="s1", intent="video", message=message)


# ─── Template / tokens ───────────────────────────────────────────────────────

def test_build_workflow_substitutes_tokens():
    wf = video.build_workflow("a cat in space", "blurry", 160, 16, 42)
    assert wf is not None
    assert wf["2"]["inputs"]["text"] == "a cat in space"
    assert wf["3"]["inputs"]["text"] == "blurry"
    assert wf["4"]["inputs"]["batch_size"] == 160         # token int
    assert wf["9"]["inputs"]["frame_rate"] == 16
    assert wf["7"]["inputs"]["seed"] == 42                # seed injecté dans KSampler


def test_parse_duration_and_prompt():
    agent = VideoAgent()
    prompt, seconds = agent._parse("génère une vidéo de 15 secondes d'un chat cosmique")
    assert seconds == 15
    assert "chat cosmique" in prompt
    assert "vidéo" not in prompt.lower()


def test_parse_default_duration():
    agent = VideoAgent()
    _, seconds = agent._parse("anime un dragon")
    assert seconds == 10   # défaut


# ─── Agent ───────────────────────────────────────────────────────────────────

async def test_video_gpu_unavailable():
    with patch("app.agents.video_agent.dispatch",
               new=AsyncMock(return_value={"ok": False, "error": "WoL échoué"})):
        resp = await VideoAgent().handle(_req())
    assert resp.status == AgentStatus.error
    assert "indisponible" in resp.content.lower()


async def test_video_job_launched():
    sub = {"ok": True, "job_id": "abc123", "frames": 240, "seconds": 15, "seed": 7}
    with patch("app.agents.video_agent.dispatch",
               new=AsyncMock(return_value={"ok": True, "model": "animatediff-sd15"})), \
         patch("app.agents.video_agent.video.submit", new=AsyncMock(return_value=sub)):
        resp = await VideoAgent().handle(_req())
    assert resp.status == AgentStatus.ok
    assert len(resp.artifacts) == 1
    art = resp.artifacts[0]
    assert art.kind == "video_job"
    assert art.url == "/api/video/status/abc123"


async def test_video_submit_failed():
    sub = {"ok": False, "error": "Template manquant"}
    with patch("app.agents.video_agent.dispatch",
               new=AsyncMock(return_value={"ok": True, "model": "animatediff-sd15"})), \
         patch("app.agents.video_agent.video.submit", new=AsyncMock(return_value=sub)):
        resp = await VideoAgent().handle(_req())
    assert resp.status == AgentStatus.error
    assert "Template manquant" in resp.content


def test_router_video_keywords():
    for phrase in ["génère une vidéo d'un chat", "anime une scène", "fais un clip de 12s"]:
        d = route(phrase, registry)
        assert d.agent == "video", f"'{phrase}' → {d.agent}"
