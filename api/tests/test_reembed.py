"""Tests ré-embedding — porte de disponibilité Ollama (mock)."""

from unittest.mock import AsyncMock, patch

from app.docs.reembed import reembed_pending


async def test_reembed_skips_when_ollama_down():
    with patch("app.docs.reembed.health", new=AsyncMock(return_value=False)):
        result = await reembed_pending()
    assert result["ok"] is False
    assert "injoignable" in result["error"].lower()
