"""Tests couche LLM — embed_batch (court-circuit) + synthèse RAG (mocks)."""

from unittest.mock import AsyncMock, patch

from app.llm import ollama
from app.llm.rag import synthesize


async def test_embed_batch_short_circuits_on_failure():
    """Dès qu'un embed renvoie None (Ollama down), les suivants sont None sans appel."""
    calls = {"n": 0}

    async def fake_embed(text, model=ollama.EMBED_MODEL):
        calls["n"] += 1
        return [0.1] if calls["n"] == 1 else None

    with patch("app.llm.ollama.embed", new=fake_embed):
        out = await ollama.embed_batch(["a", "b", "c", "d"])

    assert out[0] == [0.1]
    assert out[1] is None and out[2] is None and out[3] is None
    # b échoue → c et d ne déclenchent pas d'appel réseau
    assert calls["n"] == 2


async def test_synthesize_none_without_hits():
    assert await synthesize("question", []) is None


async def test_synthesize_none_when_llm_down():
    with patch("app.llm.rag.chat", new=AsyncMock(return_value=None)):
        out = await synthesize("q", [{"text": "x", "source": "a.pdf"}])
    assert out is None


async def test_synthesize_returns_answer():
    with patch("app.llm.rag.chat", new=AsyncMock(return_value="Réponse [1].")) as mock_chat:
        out = await synthesize("q", [{"text": "extrait", "source": "nextcloud:/a.pdf"}])
    assert out == "Réponse [1]."
    # Le contexte transmis doit nettoyer le préfixe nextcloud:
    sent = mock_chat.call_args.args[0]
    assert "nextcloud:" not in sent[1]["content"]
    assert "/a.pdf" in sent[1]["content"]
