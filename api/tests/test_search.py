"""Tests Agent Recherche et Marketing — sans Qdrant live (mocks)."""

from unittest.mock import AsyncMock, patch

from app.agents.search_agent import SearchAgent
from app.agents.marketing_agent import MarketingAgent
from app.contracts import AgentRequest, AgentStatus
from app.docs.search import _tokens
from app.registry import registry
from app.router import route

_HITS = [
    {"text": "Xenum est une solution de performance moteur premium.", "source": "fiche.pdf", "score": 3, "tags": ["xenum"]},
    {"text": "Les additifs Xenum améliorent la longévité des moteurs.", "source": "fiche.pdf", "score": 2, "tags": ["xenum"]},
]


def test_tokens_removes_stopwords():
    tokens = _tokens("quel est le produit phare de Xenum ?")
    assert "xenum" in tokens
    assert "est" not in tokens
    assert "le" not in tokens


def test_tokens_min_length():
    tokens = _tokens("CPU RAM IO")
    assert "cpu" in tokens
    assert "ram" in tokens
    # mots < 3 chars exclus
    assert "io" not in tokens


async def test_search_agent_no_docs():
    with patch("app.agents.search_agent.keyword_search", new=AsyncMock(return_value=[])):
        agent = SearchAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r1", session_id="s1",
            intent="recherche", message="trouver info xenum",
        ))
    assert resp.status == AgentStatus.ok
    assert "Aucun document" in resp.content


async def test_search_agent_with_docs():
    with patch("app.agents.search_agent.keyword_search", new=AsyncMock(return_value=_HITS)):
        agent = SearchAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r2", session_id="s1",
            intent="recherche", message="xenum performance moteur",
        ))
    assert "fiche.pdf" in resp.content
    assert "Xenum" in resp.content


async def test_marketing_agent_post_intent():
    with patch("app.agents.marketing_agent.keyword_search", new=AsyncMock(return_value=_HITS)):
        agent = MarketingAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r3", session_id="s1",
            intent="marketing", message="rédige un post instagram pour Xenum",
        ))
    assert resp.status == AgentStatus.ok
    assert "publication" in resp.content.lower() or "post" in resp.content.lower()


async def test_marketing_agent_brief_intent():
    with patch("app.agents.marketing_agent.keyword_search", new=AsyncMock(return_value=_HITS)):
        agent = MarketingAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r4", session_id="s1",
            intent="marketing", message="donne-moi des idées de campagne Xenum",
        ))
    assert "stratég" in resp.content.lower() or "angle" in resp.content.lower()


def test_router_marketing_keywords():
    for phrase in ["post instagram pour xenum", "rédige une publication",
                   "stratégie marketing xenum"]:
        d = route(phrase, registry)
        assert d.agent == "marketing", f"'{phrase}' → {d.agent}"


def test_router_recherche_keywords():
    for phrase in ["cherche dans les documents", "trouve la fiche produit"]:
        d = route(phrase, registry)
        assert d.agent == "recherche", f"'{phrase}' → {d.agent}"
