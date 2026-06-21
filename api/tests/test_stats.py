"""Tests statistiques d'usage (mocks)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as m
from app import stats

client = TestClient(m.app)


async def test_get_stats_no_pool_returns_empty():
    with patch("app.stats.get_pool", new=AsyncMock(return_value=None)):
        out = await stats.get_stats()
    assert out["totals"]["messages"] == 0
    assert out["agent_usage"] == []
    assert out["tools"]["ok"] == 0


def test_stats_endpoint_shape():
    fake = {
        "totals": {"sessions": 3, "messages": 42, "facts": 5, "tasks": 2, "media": 7},
        "agent_usage": [{"agent": "chat", "count": 20}],
        "method_breakdown": [{"method": "rules", "count": 30}],
        "messages_per_day": [{"day": "2026-06-21", "count": 42}],
        "tools": {"ok": 15, "error": 1, "top": [{"tool": "ha.get_states", "count": 4}]},
    }
    with patch("app.routers.stats.get_stats", new=AsyncMock(return_value=fake)):
        r = client.get("/api/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["totals"]["messages"] == 42
    assert data["agent_usage"][0]["agent"] == "chat"
    assert data["tools"]["ok"] == 15
