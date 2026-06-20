"""Registre des jobs de génération (vidéo, …) — visibilité opérationnelle.

En mémoire (comme app.pending) : suffisant pour une session ; les jobs ComfyUI
survivent de toute façon côté Kubuntu (history). list_jobs() rafraîchit l'état
des jobs vidéo encore en cours en interrogeant ComfyUI.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from app.media import video


@dataclass
class Job:
    id: str
    kind: str               # "video" (extensible : "image", …)
    prompt: str
    state: str = "running"  # running | done | error
    created_at: float = field(default_factory=time.time)
    view_url: str | None = None
    error: str | None = None


_jobs: dict[str, Job] = {}


def register(job_id: str, kind: str, prompt: str) -> None:
    _jobs[job_id] = Job(id=job_id, kind=kind, prompt=prompt)


async def _refresh(job: Job) -> None:
    if job.state != "running" or job.kind != "video":
        return
    st = await video.status(job.id)
    if st.get("state") == "done" and st.get("media"):
        from urllib.parse import urlencode
        m = st["media"]
        job.view_url = "/api/video/view?" + urlencode({
            "filename": m["filename"], "subfolder": m["subfolder"], "type": m["type"],
        })
        job.state = "done"
    elif st.get("state") == "error":
        job.state = "error"
        job.error = st.get("error", "échec")


async def list_jobs() -> list[dict]:
    """Rafraîchit les jobs en cours puis renvoie tous les jobs (récents d'abord)."""
    for job in _jobs.values():
        await _refresh(job)
    ordered = sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)
    return [asdict(j) for j in ordered]


def count_running() -> int:
    return sum(1 for j in _jobs.values() if j.state == "running")
