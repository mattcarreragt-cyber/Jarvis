"""Agent Vidéo — génération de vidéo 10-20 s via ComfyUI/AnimateDiff (Kubuntu GPU).

Asynchrone : lance un job et renvoie un artefact `video_job` que le dashboard
poll jusqu'à la vidéo finale (la génération prend plusieurs minutes sur 8 Go).

Capacité `video` = exclusive : le scheduler décharge LLM + image avant.
"""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.config import settings
from app.contracts import (
    AgentRequest,
    AgentResponse,
    AgentSpec,
    AgentStatus,
    Artifact,
    ToolCall,
    ToolResult,
)
from app.media import video
from app.orchestration.scheduler import dispatch

_STRIP = re.compile(
    r"\b(génère|genere|crée|cree|fais|fabrique|une?|vidéo|video|clip|animation|"
    r"séquence|montre[-\s]?moi|peux[-\s]?tu|secondes?|s)\b",
    re.I,
)
_DURATION = re.compile(r"(\d{1,2})\s*(?:s|sec|secondes?)\b", re.I)


class VideoAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="video",
            description="Génération de courtes vidéos (10-20 s) à partir d'une "
                        "description (ComfyUI/AnimateDiff sur GPU).",
            keywords=[
                "vidéo", "video", "clip", "animation", "anime", "séquence",
                "anime une", "génère une vidéo", "crée une vidéo", "motion",
            ],
            default_permissions=["video:generate"],
        )

    def _parse(self, message: str) -> tuple[str, int]:
        m = _DURATION.search(message)
        seconds = int(m.group(1)) if m else settings.video_default_seconds
        prompt = _STRIP.sub(" ", message)
        prompt = re.sub(r"\s+", " ", prompt).strip(" :,.")
        return (prompt or message), seconds

    async def handle(self, req: AgentRequest) -> AgentResponse:
        from app.config import settings
        # Palier HD via RunPod si configuré, sinon AnimateDiff local (Kubuntu)
        use_hd = settings.runpod_enabled and bool(settings.runpod_comfyui_url)
        capability = "video.hd" if use_hd else "video"

        disp = await dispatch(capability)
        if not disp.get("ok"):
            where = "RunPod" if use_hd else "Kubuntu"
            return AgentResponse(
                request_id=req.request_id, agent="video",
                status=AgentStatus.error,
                content=f"Le GPU ({where}) est indisponible, impossible de générer une vidéo.\n\n"
                        f"_{disp.get('error', 'GPU hors ligne')}._",
                tool_calls=[ToolCall(
                    tool="orchestration.dispatch", args={"capability": capability},
                    result=ToolResult(ok=False, error=disp.get("error")),
                )],
            )

        base = disp.get("base_url")
        prompt, seconds = self._parse(req.message)
        sub = await video.submit(prompt, seconds, base_url=base,
                                 workflow_path=disp.get("workflow"))
        call = ToolCall(
            tool="comfyui.video.submit",
            args={"prompt": prompt, "seconds": seconds, "capability": capability},
            result=ToolResult(ok=sub.get("ok", False),
                              data=sub if sub.get("ok") else None,
                              error=sub.get("error")),
        )

        if not sub.get("ok"):
            return AgentResponse(
                request_id=req.request_id, agent="video",
                status=AgentStatus.error,
                content=f"Impossible de lancer la génération vidéo : {sub.get('error')}.",
                tool_calls=[call],
            )

        job_id = sub["job_id"]
        from app.media import jobs
        jobs.register(job_id, kind="video", prompt=prompt, base_url=base)
        est_min = max(1, round(sub["frames"] / 60))   # estimation grossière
        return AgentResponse(
            request_id=req.request_id, agent="video",
            status=AgentStatus.ok,
            content=(
                f"🎬 Génération vidéo lancée : *{prompt}* "
                f"({sub['seconds']} s, {sub['frames']} frames, seed {sub['seed']}).\n\n"
                f"_Temps estimé ~{est_min} min. La vidéo apparaîtra ici une fois prête._"
            ),
            artifacts=[Artifact(
                kind="video_job", name=job_id,
                url=f"/api/video/status/{job_id}",
            )],
            tool_calls=[call],
        )
