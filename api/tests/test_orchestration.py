"""Tests Orchestration — scheduler + WoL (mocks)."""

from unittest.mock import AsyncMock, patch

from app.orchestration.scheduler import get_capability, resolve_chat_hint


def test_get_capability_known():
    cap = get_capability("chat.fast")
    assert cap is not None
    assert cap["machine"] == "kubuntu"
    assert cap["gpu"] is True


def test_get_capability_unknown():
    assert get_capability("inexistant") is None


def test_get_capability_tts_no_gpu():
    cap = get_capability("tts")
    assert cap["machine"] == "unraid"
    assert cap["gpu"] is False


def test_resolve_chat_hint_fast():
    assert resolve_chat_hint("dis-moi bonjour") == "fast"


def test_resolve_chat_hint_deep():
    for phrase in ["analyse ce texte", "fais une stratégie", "écris du code"]:
        assert resolve_chat_hint(phrase) == "deep", f"'{phrase}' devrait être deep"


async def test_dispatch_tts_no_wol():
    """TTS est sur Unraid (gpu=false) — pas de WoL déclenché."""
    from app.orchestration.scheduler import dispatch
    with patch("app.orchestration.scheduler.ensure_kubuntu", new=AsyncMock()) as mock_wol, \
         patch("app.orchestration.scheduler.is_kubuntu_alive", new=AsyncMock(return_value=True)):
        result = await dispatch("tts")
    assert result["ok"] is True
    mock_wol.assert_not_called()


async def test_dispatch_gpu_kubuntu_alive():
    """GPU requis, Kubuntu déjà en ligne — pas de WoL."""
    from app.orchestration.scheduler import dispatch
    with patch("app.orchestration.scheduler.is_kubuntu_alive", new=AsyncMock(return_value=True)) as mock_alive, \
         patch("app.orchestration.scheduler.ensure_kubuntu", new=AsyncMock()) as mock_wol:
        result = await dispatch("chat.fast")
    assert result["ok"] is True
    mock_wol.assert_not_called()


async def test_dispatch_gpu_kubuntu_offline_wol_ok():
    """GPU requis, Kubuntu offline → WoL appelé et réussi."""
    from app.orchestration.scheduler import dispatch
    with patch("app.orchestration.scheduler.is_kubuntu_alive", new=AsyncMock(return_value=False)), \
         patch("app.orchestration.scheduler.ensure_kubuntu", new=AsyncMock(return_value=True)):
        result = await dispatch("embeddings")
    assert result["ok"] is True


async def test_dispatch_gpu_kubuntu_offline_wol_fail():
    """GPU requis, Kubuntu offline, WoL échoue → ok=False."""
    from app.orchestration.scheduler import dispatch
    with patch("app.orchestration.scheduler.is_kubuntu_alive", new=AsyncMock(return_value=False)), \
         patch("app.orchestration.scheduler.ensure_kubuntu", new=AsyncMock(return_value=False)):
        result = await dispatch("chat.deep")
    assert result["ok"] is False
    assert "Kubuntu" in result["error"]
