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


# ─── Budget VRAM (GPU 8 Go) ──────────────────────────────────────────────────

async def test_dispatch_image_unloads_all_llms():
    """Capacité image (exclusive) → décharge tous les LLM Ollama avant de charger."""
    from app.orchestration.scheduler import dispatch
    with patch("app.orchestration.scheduler.is_kubuntu_alive", new=AsyncMock(return_value=True)), \
         patch("app.llm.ollama.unload_all", new=AsyncMock(return_value=2)) as mock_unload, \
         patch("app.llm.ollama.ps", new=AsyncMock(return_value=[])):
        result = await dispatch("image")
    assert result["ok"] is True
    mock_unload.assert_awaited_once()


async def test_dispatch_chat_within_budget_keeps_models():
    """chat.fast avec peu de VRAM utilisée → pas de déchargement."""
    from app.orchestration.scheduler import dispatch
    loaded = [{"name": "qwen2.5:7b", "size_vram": 5_000_000_000}]  # 5 Go, sous budget
    with patch("app.orchestration.scheduler.is_kubuntu_alive", new=AsyncMock(return_value=True)), \
         patch("app.llm.ollama.ps", new=AsyncMock(return_value=loaded)), \
         patch("app.llm.ollama.unload_all", new=AsyncMock(return_value=0)) as mock_unload:
        result = await dispatch("chat.fast")
    assert result["ok"] is True
    mock_unload.assert_not_awaited()


async def test_dispatch_chat_over_budget_unloads():
    """chat.deep alors qu'un gros modèle est déjà résident → dépasse 8 Go → déchargement."""
    from app.orchestration.scheduler import dispatch
    loaded = [{"name": "other", "size_vram": 7_000_000_000}]  # 7 Go + besoin 9 > 8
    with patch("app.orchestration.scheduler.is_kubuntu_alive", new=AsyncMock(return_value=True)), \
         patch("app.llm.ollama.ps", new=AsyncMock(return_value=loaded)), \
         patch("app.llm.ollama.unload_all", new=AsyncMock(return_value=1)) as mock_unload:
        result = await dispatch("chat.deep")
    assert result["ok"] is True
    assert result["vram_gb"] == 9
    mock_unload.assert_awaited_once()
