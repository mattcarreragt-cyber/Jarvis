"""Tests export + suppression de conversation — mocks."""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as m
from app.routers.sessions import _to_markdown

client = TestClient(m.app)


def _mock_pool(execute_return: str):
    """Pool factice : pool.acquire() -> conn.execute() renvoie execute_return."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=execute_return)

    class _Pool:
        @asynccontextmanager
        async def acquire(self):
            yield conn

    return _Pool()

_MSGS = [
    {"role": "user", "content": "salut", "agent": None, "created_at": "2026-06-21T10:00:00"},
    {"role": "assistant", "content": "Bonjour !", "agent": "chat", "created_at": "2026-06-21T10:00:05"},
]


def test_to_markdown_structure():
    md = _to_markdown("abcd1234ef", _MSGS)
    assert "# Conversation JARVIS" in md
    assert "Vous" in md and "salut" in md
    assert "[chat]" in md and "Bonjour !" in md


def test_export_markdown():
    with patch("app.routers.sessions._fetch_messages", new=AsyncMock(return_value=_MSGS)):
        r = client.get("/api/sessions/abcd1234/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "attachment" in r.headers["content-disposition"]
    assert "Bonjour !" in r.text


def test_export_json():
    with patch("app.routers.sessions._fetch_messages", new=AsyncMock(return_value=_MSGS)):
        r = client.get("/api/sessions/abcd1234/export?format=json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    data = json.loads(r.text)
    assert data["session_id"] == "abcd1234"
    assert len(data["messages"]) == 2


def test_delete_session_ok():
    with patch("app.routers.sessions.get_pool", new=AsyncMock(return_value=_mock_pool("DELETE 1"))):
        r = client.delete("/api/sessions/abcd1234")
    assert r.status_code == 204


def test_delete_session_not_found():
    with patch("app.routers.sessions.get_pool", new=AsyncMock(return_value=_mock_pool("DELETE 0"))):
        r = client.delete("/api/sessions/nope")
    assert r.status_code == 404
