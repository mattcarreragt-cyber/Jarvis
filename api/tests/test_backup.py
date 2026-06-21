"""Tests sauvegarde / restauration (mocks)."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as m
from app import backup

client = TestClient(m.app)


def test_serialize_datetime():
    dt = datetime(2026, 6, 21, 10, 0)
    assert backup._serialize(dt) == dt.isoformat()
    assert backup._serialize("plain") == "plain"


def test_deserialize_datetime():
    out = backup._deserialize("created_at", "2026-06-21T10:00:00")
    assert isinstance(out, datetime)
    assert backup._deserialize("text", "salut") == "salut"
    assert backup._deserialize("created_at", "pas une date") is None


async def test_export_no_pool():
    with patch("app.backup.get_pool", new=AsyncMock(return_value=None)):
        data = await backup.export_all()
    assert data["version"] == backup.VERSION
    assert data["tables"] == {}


async def test_import_invalid_format():
    with patch("app.backup.get_pool", new=AsyncMock(return_value=object())):
        res = await backup.import_all({"nope": 1})
    assert res["ok"] is False


async def test_import_no_pool():
    with patch("app.backup.get_pool", new=AsyncMock(return_value=None)):
        res = await backup.import_all({"tables": {}})
    assert res["ok"] is False


def test_download_endpoint():
    fake = {"version": 1, "generated_at": "2026-06-21T10:00:00",
            "tables": {"memory_facts": [], "scheduled_tasks": [], "webhooks": []}}
    with patch("app.routers.backup.export_all", new=AsyncMock(return_value=fake)):
        r = client.get("/api/backup")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert json.loads(r.text)["version"] == 1


def test_restore_endpoint_bad_mode():
    r = client.post("/api/backup/restore?mode=wrong",
                    files={"file": ("b.json", b"{}", "application/json")})
    assert r.status_code == 400


def test_restore_endpoint_ok():
    payload = json.dumps({"tables": {"memory_facts": [], "scheduled_tasks": [], "webhooks": []}})
    with patch("app.routers.backup.import_all",
               new=AsyncMock(return_value={"ok": True, "mode": "merge", "imported": {}})):
        r = client.post("/api/backup/restore",
                        files={"file": ("b.json", payload.encode(), "application/json")})
    assert r.status_code == 200
    assert r.json()["ok"] is True
