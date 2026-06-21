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
    base_url: str | None = None   # endpoint ComfyUI (RunPod) si applicable


_jobs: dict[str, Job] = {}


def register(job_id: str, kind: str, prompt: str, base_url: str | None = None) -> None:
    _jobs[job_id] = Job(id=job_id, kind=kind, prompt=prompt, base_url=base_url)


def get(job_id: str) -> Job | None:
    return _jobs.get(job_id)


async def _refresh(job: Job) -> None:
    if job.state != "running" or job.kind != "video":
        return
    st = await video.status(job.id, base_url=job.base_url)
    if st.get("state") == "done" and st.get("media"):
        from urllib.parse import urlencode
        m = st["media"]
        params = {"filename": m["filename"], "subfolder": m["subfolder"], "type": m["type"]}
        if job.base_url:
            params["src"] = job.base_url
        job.view_url = "/api/video/view?" + urlencode(params)
        job.state = "done"
        # Enregistre la vidéo terminée dans la galerie durable
        from app.media import gallery
        await gallery.add_asset("video", m["filename"], m["subfolder"], m["type"],
                                prompt=job.prompt, base_url=job.base_url)
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
