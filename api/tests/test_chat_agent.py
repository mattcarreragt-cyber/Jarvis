"""Tests Agent Chat généraliste — dispatch/WoL + LLM (mocks)."""

from unittest.mock import AsyncMock, patch

from app.agents.chat_agent import ChatAgent
from app.contracts import AgentRequest, AgentStatus, MemoryContext, Turn


def _req(message="bonjour", ctx=None, hint=None):
    return AgentRequest(
        request_id="c1", session_id="s1", intent="chat",
        message=message, context=ctx or MemoryContext(), hint=hint,
    )


async def test_chat_kubuntu_unavailable():
    """dispatch échoue (Kubuntu down, WoL KO) → message d'erreur clair."""
    with patch("app.agents.chat_agent.dispatch",
               new=AsyncMock(return_value={"ok": False, "error": "WoL échoué"})):
        resp = await ChatAgent().handle(_req())
    assert resp.status == AgentStatus.error
    assert "indisponible" in resp.content.lower()
    assert "WoL échoué" in resp.content


async def test_chat_success():
    with patch("app.agents.chat_agent.dispatch",
               new=AsyncMock(return_value={"ok": True, "model": "llama3.1:8b"})), \
         patch("app.agents.chat_agent.chat", new=AsyncMock(return_value="Bonjour !")) as mock_chat:
        resp = await ChatAgent().handle(_req("salut"))
    assert resp.status == AgentStatus.ok
    assert resp.content == "Bonjour !"
    # le modèle résolu par dispatch est bien transmis à chat()
    assert mock_chat.call_args.kwargs["model"] == "llama3.1:8b"


async def test_chat_kubuntu_up_but_no_answer():
    with patch("app.agents.chat_agent.dispatch",
               new=AsyncMock(return_value={"ok": True, "model": "llama3.1:8b"})), \
         patch("app.agents.chat_agent.chat", new=AsyncMock(return_value=None)):
        resp = await ChatAgent().handle(_req())
    assert resp.status == AgentStatus.error
    assert "modèle" in resp.content.lower()


async def test_chat_uses_hint_deep():
    """Le hint explicite 'deep' sélectionne la capacité chat.deep."""
    captured = {}

    async def fake_dispatch(cap):
        captured["cap"] = cap
        return {"ok": True, "model": "llama3.1:70b"}

    with patch("app.agents.chat_agent.dispatch", new=fake_dispatch), \
         patch("app.agents.chat_agent.chat", new=AsyncMock(return_value="ok")):
        await ChatAgent().handle(_req("analyse ceci", hint="deep"))
    assert captured["cap"] == "chat.deep"


async def test_chat_builds_context_messages():
    ctx = MemoryContext(
        recent_turns=[Turn(role="user", content="je m'appelle Matt"),
                      Turn(role="assistant", content="enchanté Matt")],
        relevant_memories=["L'utilisateur travaille pour Xenum"],
    )
    captured = {}

    async def fake_chat(messages, model=None, temperature=0.7):
        captured["messages"] = messages
        return "réponse"

    with patch("app.agents.chat_agent.dispatch",
               new=AsyncMock(return_value={"ok": True, "model": "m"})), \
         patch("app.agents.chat_agent.chat", new=fake_chat):
        await ChatAgent().handle(_req("et moi ?", ctx=ctx))

    msgs = captured["messages"]
    assert msgs[0]["role"] == "system"
    joined = " ".join(m["content"] for m in msgs)
    assert "Xenum" in joined            # souvenir injecté
    assert "je m'appelle Matt" in joined  # tour récent injecté
    assert msgs[-1]["content"] == "et moi ?"  # message courant en dernier
