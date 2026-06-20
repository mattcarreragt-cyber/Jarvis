"""Tests RunPod — ensure_runpod + dispatch(machine=runpod) + hint xl (mocks)."""

from unittest.mock import AsyncMock, patch

from app.orchestration import runpod
from app.orchestration.scheduler import dispatch, get_capability, resolve_chat_hint


def test_capabilities_runpod_present():
    assert get_capability("chat.xl")["machine"] == "runpod"
    assert get_capability("video.hd")["machine"] == "runpod"


async def test_ensure_runpod_disabled():
    with patch.object(runpod.settings, "runpod_enabled", False):
        res = await runpod.ensure_runpod("ollama")
    assert res["ok"] is False


async def test_ensure_runpod_alive():
    with patch.object(runpod.settings, "runpod_enabled", True), \
         patch.object(runpod.settings, "runpod_ollama_url", "http://pod:11434"), \
         patch("app.orchestration.runpod.is_backend_alive", new=AsyncMock(return_value=True)):
        res = await runpod.ensure_runpod("ollama")
    assert res["ok"] is True
    assert res["base_url"] == "http://pod:11434"


async def test_ensure_runpod_starts_pod():
    calls = {"alive": 0}

    async def fake_alive(url, backend):
        calls["alive"] += 1
        return calls["alive"] > 1     # injoignable d'abord, puis OK après start

    with patch.object(runpod.settings, "runpod_enabled", True), \
         patch.object(runpod.settings, "runpod_ollama_url", "http://pod:11434"), \
         patch.object(runpod.settings, "runpod_api_key", "k"), \
         patch.object(runpod.settings, "runpod_pod_id", "pod1"), \
         patch.object(runpod.settings, "runpod_start_timeout", 30), \
         patch("app.orchestration.runpod.is_backend_alive", new=fake_alive), \
         patch("app.orchestration.runpod.start_pod", new=AsyncMock(return_value=True)), \
         patch("asyncio.sleep", new=AsyncMock()):
        res = await runpod.ensure_runpod("ollama")
    assert res["ok"] is True


async def test_dispatch_runpod_capability():
    with patch("app.orchestration.runpod.ensure_runpod",
               new=AsyncMock(return_value={"ok": True, "base_url": "http://pod:11434"})):
        res = await dispatch("chat.xl")
    assert res["ok"] is True
    assert res["machine"] == "runpod"
    assert res["base_url"] == "http://pod:11434"
    assert res["model"] == "qwen2.5:72b"


async def test_dispatch_runpod_unavailable():
    with patch("app.orchestration.runpod.ensure_runpod",
               new=AsyncMock(return_value={"ok": False, "error": "pod down"})):
        res = await dispatch("video.hd")
    assert res["ok"] is False
    assert "pod down" in res["error"]


def test_resolve_hint_xl_requires_runpod():
    from app.config import settings
    # désactivé → jamais xl
    with patch.object(settings, "runpod_enabled", False):
        assert resolve_chat_hint("utilise un gros modèle") != "xl"
    # activé → xl sur déclencheur
    with patch.object(settings, "runpod_enabled", True):
        assert resolve_chat_hint("utilise un gros modèle") == "xl"
