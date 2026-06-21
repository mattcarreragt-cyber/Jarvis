"""Agent Audio — génération de musique / sons via ComfyUI (Stable Audio), Kubuntu GPU.

Capacité `audio` = exclusive : le scheduler décharge les LLM avant.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode

from app.agents.base import Agent
from app.config import settings
from app.contracts import (
    AgentRequest, AgentResponse, AgentSpec, AgentStatus, Artifact, ToolCall, ToolResult,
)
from app.media import audio
from app.orchestration.scheduler import dispatch

_STRIP = re.compile(
    r"\b(génère|genere|crée|cree|compose|fais|une?|de\s+la|du|musique|son|audio|"
    r"jingle|mélodie|melodie|bruitage|piste|morceau|secondes?|s)\b", re.I,
)
_DURATION = re.compile(r"(\d{1,2})\s*(?:s|sec|secondes?)\b", re.I)


class AudioAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="audio",
            description="Génération de musique, sons, jingles et bruitages à partir "
                        "d'une description (Stable Audio sur GPU).",
            keywords=[
                "musique", "audio", "jingle", "mélodie", "melodie",
                "bruitage", "morceau", "compose", "piste sonore", "ambiance sonore",
                "sample audio", "musical",
            ],
            default_permissions=["audio:generate"],
        )

    def _parse(self, message: str) -> tuple[str, int]:
        m = _DURATION.search(message)
        seconds = int(m.group(1)) if m else settings.audio_default_seconds
        prompt = _STRIP.sub(" ", message)
        prompt = re.sub(r"\s+", " ", prompt).strip(" :,.")
        return (prompt or message), seconds

    async def handle(self, req: AgentRequest) -> AgentResponse:
        disp = await dispatch("audio")
        if not disp.get("ok"):
            return AgentResponse(
                request_id=req.request_id, agent="audio", status=AgentStatus.error,
                content="Le GPU (Kubuntu) est indisponible, impossible de générer de l'audio.\n\n"
                        f"_{disp.get('error', 'GPU hors ligne')}._",
                tool_calls=[ToolCall(tool="orchestration.dispatch", args={"capability": "audio"},
                                     result=ToolResult(ok=False, error=disp.get("error")))],
            )

        base = disp.get("base_url")
        prompt, seconds = self._parse(req.message)
        result = await audio.generate(prompt, seconds, base_url=base,
                                      workflow_path=disp.get("workflow"))
        call = ToolCall(tool="comfyui.audio.generate",
                        args={"prompt": prompt, "seconds": seconds},
                        result=ToolResult(ok=result is not None, data=result,
                                          error=None if result else "Génération échouée / ComfyUI injoignable"))

        if not result:
            return AgentResponse(
                request_id=req.request_id, agent="audio", status=AgentStatus.error,
                content="Kubuntu est joignable mais la génération audio a échoué. "
                        "Vérifie que le modèle Stable Audio est installé dans ComfyUI.",
                tool_calls=[call])

        params = {"filename": result["filename"], "subfolder": result["subfolder"],
                  "type": result["type"]}
        if base:
            params["src"] = base
        url = f"/api/audio/view?{urlencode(params)}"

        from app.media import gallery
        await gallery.add_asset("audio", result["filename"], result["subfolder"],
                                result["type"], prompt=prompt, base_url=base)

        return AgentResponse(
            request_id=req.request_id, agent="audio", status=AgentStatus.ok,
            content=f"🎵 Audio généré pour : *{prompt}* ({seconds}s, seed {result['seed']}).",
            artifacts=[Artifact(kind="audio", name=result["filename"], url=url)],
            tool_calls=[call])
