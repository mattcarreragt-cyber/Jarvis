"""Tests registre de jobs de génération (mocks ComfyUI)."""

from unittest.mock import AsyncMock, patch

from app.media import jobs


def setup_function():
    jobs._jobs.clear()


def test_register_and_count():
    jobs.register("j1", "video", "un chat")
    assert jobs.count_running() == 1


async def test_list_refreshes_done():
    jobs.register("j1", "video", "un chat")
    done = {"state": "done", "media": {"filename": "out.mp4", "subfolder": "", "type": "output"}}
    with patch("app.media.jobs.video.status", new=AsyncMock(return_value=done)):
        items = await jobs.list_jobs()
    assert items[0]["state"] == "done"
    assert "out.mp4" in items[0]["view_url"]
    assert jobs.count_running() == 0


async def test_list_marks_error():
    jobs.register("j2", "video", "raté")
    with patch("app.media.jobs.video.status",
               new=AsyncMock(return_value={"state": "error", "error": "boom"})):
        items = await jobs.list_jobs()
    assert items[0]["state"] == "error"
    assert items[0]["error"] == "boom"


async def test_list_running_stays_running():
    jobs.register("j3", "video", "en cours")
    with patch("app.media.jobs.video.status", new=AsyncMock(return_value={"state": "running"})):
        items = await jobs.list_jobs()
    assert items[0]["state"] == "running"


async def test_done_job_not_refetched():
    """Un job déjà terminé n'interroge plus ComfyUI."""
    jobs.register("j4", "video", "fini")
    jobs._jobs["j4"].state = "done"
    with patch("app.media.jobs.video.status", new=AsyncMock()) as mock_status:
        await jobs.list_jobs()
    mock_status.assert_not_awaited()
