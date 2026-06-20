"""Tests Agent Image — dispatch GPU + ComfyUI (mocks)."""

from unittest.mock import AsyncMock, patch

from app.agents.image_agent import ImageAgent
from app.contracts import AgentRequest, AgentStatus
from app.registry import registry
from app.router import route


def _req(message="génère une image d'un moteur Xenum"):
    return AgentRequest(request_id="i1", session_id="s1", intent="image", message=message)


def test_to_prompt_strips_commands():
    agent = ImageAgent()
    p = agent._to_prompt("génère une image d'un chat cosmique")
    assert "génère" not in p.lower()
    assert "chat cosmique" in p


async def test_image_gpu_unavailable():
    with patch("app.agents.image_agent.dispatch",
               new=AsyncMock(return_value={"ok": False, "error": "WoL échoué"})):
        resp = await ImageAgent().handle(_req())
    assert resp.status == AgentStatus.error
    assert "indisponible" in resp.content.lower()


async def test_image_success_returns_artifact():
    gen = {"filename": "jarvis_001.png", "subfolder": "", "type": "output", "seed": 42}
    with patch("app.agents.image_agent.dispatch",
               new=AsyncMock(return_value={"ok": True, "model": "sdxl"})), \
         patch("app.agents.image_agent.comfyui.generate", new=AsyncMock(return_value=gen)):
        resp = await ImageAgent().handle(_req())
    assert resp.status == AgentStatus.ok
    assert len(resp.artifacts) == 1
    art = resp.artifacts[0]
    assert art.kind == "image"
    assert "jarvis_001.png" in art.url
    assert art.url.startswith("/api/images/view?")


async def test_image_generation_failed():
    with patch("app.agents.image_agent.dispatch",
               new=AsyncMock(return_value={"ok": True, "model": "sdxl"})), \
         patch("app.agents.image_agent.comfyui.generate", new=AsyncMock(return_value=None)):
        resp = await ImageAgent().handle(_req())
    assert resp.status == AgentStatus.error
    assert "checkpoint" in resp.content.lower()


def test_router_image_keywords():
    for phrase in ["dessine un logo", "génère une image de moteur", "crée une illustration"]:
        d = route(phrase, registry)
        assert d.agent == "image", f"'{phrase}' → {d.agent}"
