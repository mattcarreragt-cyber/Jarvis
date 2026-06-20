"""Tests image→vidéo — tokens, upload, submit, endpoint (mocks)."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as m
from app.media import video

client = TestClient(m.app)


def test_img2vid_workflow_tokens():
    wf = video.build_img2vid_workflow("photo.png", 25, 8, 42)
    assert wf is not None
    assert wf["2"]["inputs"]["image"] == "photo.png"     # __IMAGE__
    assert wf["3"]["inputs"]["video_frames"] == 25       # __FRAMES__
    assert wf["3"]["inputs"]["fps"] == 8                 # __FPS__
    assert wf["7"]["inputs"]["frame_rate"] == 8
    assert wf["5"]["inputs"]["seed"] == 42               # seed injecté


def test_apply_tokens_generic():
    out = video._apply_tokens({"a": "__IMAGE__", "b": ["__FRAMES__", "x"]},
                              {"__IMAGE__": "im.png", "__FRAMES__": 10})
    assert out == {"a": "im.png", "b": [10, "x"]}


async def test_submit_img2vid_upload_fails():
    with patch("app.media.video.upload_image", new=AsyncMock(return_value=None)):
        res = await video.submit_img2vid(b"img", "a.png", 5)
    assert res["ok"] is False
    assert "upload" in res["error"].lower()


async def test_submit_img2vid_ok():
    with patch("app.media.video.upload_image", new=AsyncMock(return_value="a.png")), \
         patch("app.media.video._submit_workflow", new=AsyncMock(return_value={"ok": True, "job_id": "J1"})):
        res = await video.submit_img2vid(b"img", "a.png", 5)
    assert res["ok"] is True
    assert res["job_id"] == "J1"
    assert res["frames"] == 5 * video.settings.video_fps


def test_animate_endpoint_ok():
    with patch("app.routers.video.dispatch",
               new=AsyncMock(return_value={"ok": True, "base_url": None})), \
         patch("app.routers.video.video.submit_img2vid",
               new=AsyncMock(return_value={"ok": True, "job_id": "J9", "seconds": 5, "frames": 80})):
        r = client.post("/api/video/animate",
                        files={"file": ("cat.png", b"img", "image/png")},
                        data={"seconds": "5"})
    assert r.status_code == 200
    assert r.json()["job_id"] == "J9"


def test_animate_endpoint_gpu_down():
    with patch("app.routers.video.dispatch",
               new=AsyncMock(return_value={"ok": False, "error": "GPU off"})):
        r = client.post("/api/video/animate",
                        files={"file": ("cat.png", b"img", "image/png")},
                        data={"seconds": "5"})
    assert r.status_code == 503
