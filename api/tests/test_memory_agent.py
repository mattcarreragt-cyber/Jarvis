"""Tests Agent Mémoire + fusion de contexte (mocks, sans Postgres live)."""

from unittest.mock import AsyncMock, patch

from app.agents.memory_agent import MemoryAgent
from app.contracts import AgentRequest, AgentStatus
from app.registry import registry
from app.router import route


def _req(message):
    return AgentRequest(request_id="m1", session_id="s1", intent="memoire", message=message)


async def test_remember_fact():
    with patch("app.agents.memory_agent.facts.add_fact", new=AsyncMock(return_value=True)) as add, \
         patch("app.memory.long_term.LongTermMemory.remember", new=AsyncMock(return_value=False)):
        resp = await MemoryAgent().handle(_req("souviens-toi que je préfère le café noir"))
    assert resp.status == AgentStatus.ok
    assert "café noir" in resp.content
    add.assert_awaited_once()
    assert "café noir" in add.call_args.args[0]


async def test_remember_failure():
    with patch("app.agents.memory_agent.facts.add_fact", new=AsyncMock(return_value=False)), \
         patch("app.memory.long_term.LongTermMemory.remember", new=AsyncMock(return_value=False)):
        resp = await MemoryAgent().handle(_req("retiens que j'habite à Lyon"))
    assert resp.status == AgentStatus.error


async def test_recall_lists_facts():
    items = [{"id": "1", "text": "Aime le café noir", "kind": "fact", "created_at": "2026-01-01"}]
    with patch("app.agents.memory_agent.facts.list_facts", new=AsyncMock(return_value=items)):
        resp = await MemoryAgent().handle(_req("que sais-tu sur moi ?"))
    assert "café noir" in resp.content


async def test_recall_empty():
    with patch("app.agents.memory_agent.facts.list_facts", new=AsyncMock(return_value=[])):
        resp = await MemoryAgent().handle(_req("mon profil"))
    assert "rien mémorisé" in resp.content.lower()


async def test_forget_all():
    with patch("app.agents.memory_agent.facts.clear_facts", new=AsyncMock(return_value=3)):
        resp = await MemoryAgent().handle(_req("oublie tout"))
    assert "3 fait" in resp.content


async def test_help_fallback():
    resp = await MemoryAgent().handle(_req("mémoire"))
    assert "souviens-toi" in resp.content.lower()


def test_router_memory_keywords():
    for phrase in ["souviens-toi que j'aime le thé", "retiens mon adresse", "oublie tout"]:
        d = route(phrase, registry)
        assert d.agent == "memoire", f"'{phrase}' → {d.agent}"


async def test_build_context_merges_durable_and_semantic():
    from app.memory import Memory
    mem = Memory()
    with patch("app.memory.facts.search_facts", new=AsyncMock(return_value=["fait durable"])), \
         patch.object(mem.long, "recall", new=AsyncMock(return_value=["fait durable", "souvenir sémantique"])), \
         patch.object(mem.short, "recent", new=AsyncMock(return_value=[])):
        ctx = await mem.build_context("s1", "question")
    # Dédoublonné, durable d'abord
    assert ctx.relevant_memories == ["fait durable", "souvenir sémantique"]
