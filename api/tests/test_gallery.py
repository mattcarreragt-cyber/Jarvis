"""Tests galerie média — construction des view_url + endpoint (mocks)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as m
from app.media import gallery

client = TestClient(m.app)


def test_view_url_image_local():
    url = gallery._view_url("image", "a.png", "", "output", None)
    assert url.startswith("/api/images/view?")
    assert "a.png" in url
    assert "src=" not in url


def test_view_url_video_runpod():
    url = gallery._view_url("video", "c.mp4", "sub", "output", "http://pod:8188")
    assert url.startswith("/api/video/view?")
    assert "src=" in url


async def test_add_asset_no_pool():
    with patch("app.media.gallery.get_pool", new=AsyncMock(return_value=None)):
        assert await gallery.add_asset("image", "a.png") is None


def test_media_endpoint_lists():
    assets = [{"id": "1", "kind": "image", "prompt": "chat", "created_at": "2026-01-01",
               "view_url": "/api/images/view?filename=a.png"}]
    with patch("app.routers.media.gallery.list_assets", new=AsyncMock(return_value=assets)):
        r = client.get("/api/media")
    assert r.status_code == 200
    assert r.json()["assets"][0]["view_url"].startswith("/api/images/view")


def test_media_delete():
    with patch("app.routers.media.gallery.delete_asset", new=AsyncMock(return_value=True)):
        r = client.delete("/api/media/abc")
    assert r.status_code == 200
    assert r.json()["ok"] is True
