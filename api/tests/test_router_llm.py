"""Tests router passe 2 (classification LLM) — mocks."""

from unittest.mock import AsyncMock, patch

from app.registry import registry
from app.router import classify_llm, route_smart


async def test_smart_keeps_confident_rules_without_llm():
    """Mot-clé matché → décision règles, le LLM n'est pas appelé."""
    with patch("app.router.classify_llm", new=AsyncMock()) as mock_llm:
        d = await route_smart("génère une image d'un chat", registry)
    assert d.agent == "image"
    assert d.method == "rules"
    mock_llm.assert_not_awaited()


async def test_smart_uses_llm_on_no_match():
    with patch("app.router.classify_llm", new=AsyncMock(return_value="marketing")):
        d = await route_smart("blibli blabla totalement ambigu xyz", registry)
    assert d.agent == "marketing"
    assert d.method == "llm"


async def test_smart_falls_back_to_chat_when_llm_down():
    with patch("app.router.classify_llm", new=AsyncMock(return_value=None)):
        d = await route_smart("blibli blabla totalement ambigu xyz", registry)
    assert d.agent == "chat"
    assert d.method == "rules"


async def test_smart_ignores_invalid_llm_name():
    with patch("app.router.classify_llm", new=AsyncMock(return_value="inexistant")):
        d = await route_smart("blibli blabla xyz", registry)
    assert d.agent == "chat"


async def test_smart_forced_agent_skips_llm():
    with patch("app.router.classify_llm", new=AsyncMock()) as mock_llm:
        d = await route_smart("peu importe", registry, force_agent="dev")
    assert d.agent == "dev"
    assert d.method == "forced"
    mock_llm.assert_not_awaited()


async def test_classify_parses_agent_name():
    with patch("app.llm.ollama.chat", new=AsyncMock(return_value="  Marketing.\n")):
        name = await classify_llm("rédige un post", registry)
    assert name == "marketing"


async def test_classify_none_when_llm_unavailable():
    with patch("app.llm.ollama.chat", new=AsyncMock(return_value=None)):
        name = await classify_llm("un message", registry)
    assert name is None


async def test_classify_none_on_unknown_answer():
    with patch("app.llm.ollama.chat", new=AsyncMock(return_value="je ne sais pas trop")):
        name = await classify_llm("un message", registry)
    assert name is None
