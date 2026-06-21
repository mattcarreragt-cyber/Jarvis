"""Tests endpoint Système (mocks)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as m

client = TestClient(m.app)


def test_system_overview_kubuntu_offline():
    with patch("app.routers.system.ollama.health", new=AsyncMock(return_value=False)):
        r = client.get("/api/system")
    assert r.status_code == 200
    data = r.json()
    paliers = {p["name"]: p["status"] for p in data["paliers"]}
    assert paliers["Unraid"] == "online"
    assert paliers["Kubuntu"] == "offline"
    assert paliers["RunPod"] == "disabled"          # RUNPOD_ENABLED=false par défaut
    assert any(c["name"] == "chat.fast" for c in data["capabilities"])
    assert any(a["name"] == "agenda" for a in data["agents"])


def test_system_overview_kubuntu_online():
    with patch("app.routers.system.ollama.health", new=AsyncMock(return_value=True)):
        r = client.get("/api/system")
    paliers = {p["name"]: p["status"] for p in r.json()["paliers"]}
    assert paliers["Kubuntu"] == "online"
