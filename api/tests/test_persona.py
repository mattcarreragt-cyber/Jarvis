"""Tests persona / unrestricted_mode."""

from unittest.mock import patch

from app.llm import persona


def test_assistant_default_vs_unrestricted():
    with patch.object(persona.settings, "unrestricted_mode", False):
        std = persona.assistant_system()
    with patch.object(persona.settings, "unrestricted_mode", True):
        neutre = persona.assistant_system()
    assert std != neutre
    assert "ne refuses pas" in neutre.lower()


def test_rag_system_cites_sources_both_modes():
    with patch.object(persona.settings, "unrestricted_mode", False):
        assert "[1]" in persona.rag_system()
    with patch.object(persona.settings, "unrestricted_mode", True):
        s = persona.rag_system()
    assert "[1]" in s
    assert "avertissement" in s.lower()


def test_marketing_extra_only_in_unrestricted():
    with patch.object(persona.settings, "unrestricted_mode", False):
        assert persona.marketing_extra() == ""
    with patch.object(persona.settings, "unrestricted_mode", True):
        assert persona.marketing_extra() != ""


async def test_chat_agent_uses_persona():
    from unittest.mock import AsyncMock
    from app.agents.chat_agent import ChatAgent
    from app.contracts import AgentRequest, MemoryContext

    captured = {}

    async def fake_chat(messages, model=None, temperature=0.7, base_url=None, timeout=None):
        captured["sys"] = messages[0]["content"]
        return "ok"

    with patch.object(persona.settings, "unrestricted_mode", True), \
         patch("app.agents.chat_agent.dispatch",
               new=AsyncMock(return_value={"ok": True, "model": "m"})), \
         patch("app.agents.chat_agent.chat", new=fake_chat):
        await ChatAgent().handle(AgentRequest(
            request_id="c1", session_id="s1", intent="chat",
            message="salut", context=MemoryContext()))

    assert "ne refuses pas" in captured["sys"].lower()
