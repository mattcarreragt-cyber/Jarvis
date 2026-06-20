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
    with patch("app.agents.search_agent.search", new=AsyncMock(return_value=([], "keyword"))):
        agent = SearchAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r1", session_id="s1",
            intent="recherche", message="trouver info xenum",
        ))
    assert resp.status == AgentStatus.ok
    assert "Aucun document" in resp.content


async def test_search_agent_with_docs_keyword_fallback():
    """LLM indisponible → extraits bruts."""
    with patch("app.agents.search_agent.search", new=AsyncMock(return_value=(_HITS, "keyword"))), \
         patch("app.agents.rag_reply.synthesize", new=AsyncMock(return_value=None)):
        agent = SearchAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r2", session_id="s1",
            intent="recherche", message="xenum performance moteur",
        ))
    assert "fiche.pdf" in resp.content
    assert "Xenum" in resp.content


async def test_search_agent_llm_synthesis():
    """LLM dispo → réponse rédigée + bloc sources."""
    with patch("app.agents.search_agent.search", new=AsyncMock(return_value=(_HITS, "semantic"))), \
         patch("app.agents.rag_reply.synthesize", new=AsyncMock(return_value="Xenum est premium [1].")):
        agent = SearchAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r2b", session_id="s1",
            intent="recherche", message="c'est quoi xenum",
        ))
    assert "Xenum est premium" in resp.content
    assert "Sources" in resp.content
    assert "fiche.pdf" in resp.content


async def test_marketing_agent_post_intent_template():
    """Sans LLM → template de structure de post."""
    with patch("app.agents.marketing_agent.search", new=AsyncMock(return_value=(_HITS, "keyword"))), \
         patch("app.agents.marketing_agent.chat", new=AsyncMock(return_value=None)):
        agent = MarketingAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r3", session_id="s1",
            intent="marketing", message="rédige un post instagram pour Xenum",
        ))
    assert resp.status == AgentStatus.ok
    assert "publication" in resp.content.lower() or "post" in resp.content.lower()


async def test_marketing_agent_llm_generation():
    """Avec LLM → contenu généré renvoyé tel quel."""
    with patch("app.agents.marketing_agent.search", new=AsyncMock(return_value=(_HITS, "semantic"))), \
         patch("app.agents.marketing_agent.chat",
               new=AsyncMock(return_value="🔥 Xenum, la performance ultime. #xenum")):
        agent = MarketingAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r3b", session_id="s1",
            intent="marketing", message="rédige un post instagram pour Xenum",
        ))
    assert "performance ultime" in resp.content


async def test_marketing_agent_brief_intent_template():
    with patch("app.agents.marketing_agent.search", new=AsyncMock(return_value=(_HITS, "keyword"))), \
         patch("app.agents.marketing_agent.chat", new=AsyncMock(return_value=None)):
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
