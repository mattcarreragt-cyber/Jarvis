"""Tests webhooks — déclenchement par token + gestion (mocks)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as m

client = TestClient(m.app)


def test_new_token_unique():
    from app.automation import hooks
    assert hooks.new_token() != hooks.new_token()


def test_trigger_unknown_token_404():
    with patch("app.routers.hooks.hooks.get_by_token", new=AsyncMock(return_value=None)):
        r = client.post("/api/hooks/badtoken")
    assert r.status_code == 404


def test_trigger_known_token_returns_queued():
    hook = {"id": "h1", "label": "brief", "message": "cpu et ram", "enabled": True}
    with patch("app.routers.hooks.hooks.get_by_token", new=AsyncMock(return_value=hook)), \
         patch("app.routers.hooks.execute_hook", new=AsyncMock()):
        r = client.post("/api/hooks/goodtoken")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["label"] == "brief"


async def test_execute_hook_runs_and_notifies():
    hook = {"id": "h1", "label": "brief", "message": "cpu et ram"}
    from app.routers.hooks import execute_hook
    with patch("app.routers.hooks.runner._run_prompt", new=AsyncMock(return_value="résultat")) as run, \
         patch("app.routers.hooks.store.add_notification", new=AsyncMock()) as notif, \
         patch("app.routers.hooks.hooks.mark_triggered", new=AsyncMock()) as mark:
        await execute_hook(hook)
    run.assert_awaited_once()
    notif.assert_awaited_once()
    assert "webhook:brief" in notif.call_args.kwargs["source"]
    mark.assert_awaited_once()


def test_trigger_disabled_hook_404():
    hook = {"id": "h1", "label": "x", "message": "y", "enabled": False}
    with patch("app.routers.hooks.hooks.get_by_token", new=AsyncMock(return_value=hook)):
        r = client.post("/api/hooks/sometoken")
    assert r.status_code == 404


def test_create_hook():
    created = {"id": "h2", "token": "tok", "label": "brief", "message": "résume"}
    with patch("app.routers.hooks.hooks.create_hook", new=AsyncMock(return_value=created)):
        r = client.post("/api/hooks", json={"label": "brief", "message": "résume"})
    assert r.status_code == 200
    assert r.json()["token"] == "tok"


def test_list_hooks():
    with patch("app.routers.hooks.hooks.list_hooks", new=AsyncMock(return_value=[])):
        r = client.get("/api/hooks")
    assert r.status_code == 200
    assert r.json() == {"hooks": []}
