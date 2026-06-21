"""Tests endpoints Home Assistant (mocks)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as m
from app.contracts import ToolResult

client = TestClient(m.app)


def test_ha_states_ok():
    data = {"states": [{"entity_id": "sensor.temp", "state": "21.4", "friendly_name": "Temp"}], "total": 1}
    with patch("app.routers.ha.get_states", new=AsyncMock(return_value=ToolResult(ok=True, data=data))):
        r = client.get("/api/ha/states?domain=sensor")
    assert r.status_code == 200
    assert r.json()["states"][0]["state"] == "21.4"


def test_ha_states_unreachable():
    with patch("app.routers.ha.get_states",
               new=AsyncMock(return_value=ToolResult(ok=False, error="injoignable"))):
        r = client.get("/api/ha/states")
    assert r.status_code == 502


def test_ha_toggle_on():
    with patch("app.routers.ha.turn_on", new=AsyncMock(return_value=ToolResult(ok=True))) as on:
        r = client.post("/api/ha/toggle", json={"entity_id": "light.salon", "on": True})
    assert r.status_code == 200
    assert r.json()["on"] is True
    on.assert_awaited_once()


def test_ha_toggle_off():
    with patch("app.routers.ha.turn_off", new=AsyncMock(return_value=ToolResult(ok=True))) as off:
        r = client.post("/api/ha/toggle", json={"entity_id": "light.salon", "on": False})
    assert r.status_code == 200
    off.assert_awaited_once()
