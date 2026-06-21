"""Agent Image — génération d'images via ComfyUI/SDXL (Kubuntu GPU).

Capacité `image` = exclusive : le scheduler décharge tous les LLM avant (8 Go VRAM).
Best-effort : si Kubuntu/ComfyUI est indisponible → message clair.

L'URL renvoyée pointe vers le proxy de l'API (/api/images/view…), qui va chercher
l'image sur Kubuntu — le dashboard n'accède jamais directement au nœud GPU.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode

from app.agents.base import Agent
from app.contracts import (
    AgentRequest,
    AgentResponse,
    AgentSpec,
    AgentStatus,
    Artifact,
    ToolCall,
    ToolResult,
)
from app.media import comfyui
from app.orchestration.scheduler import dispatch

# Nettoie la requête pour en faire un prompt (retire les verbes de commande)
_STRIP = re.compile(
    r"\b(génère|genere|crée|cree|dessine|fais|fabrique|une?|image|illustration|"
    r"visuel|photo|rendu|montre[-\s]?moi|peux[-\s]?tu)\b",
    re.I,
)


class ImageAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="image",
            description="Génération d'images à partir d'une description "
                        "(ComfyUI/SDXL sur GPU). Visuels, illustrations, images de pub.",
            keywords=[
                "image", "dessine", "illustration", "visuel", "génère une image",
                "crée une image", "rendu", "photo", "logo", "bannière", "affiche",
                "sdxl", "comfyui",
            ],
            default_permissions=["image:generate"],
        )

    def _to_prompt(self, message: str) -> str:
        cleaned = _STRIP.sub(" ", message)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" :,.")
        return cleaned or message

    async def handle(self, req: AgentRequest) -> AgentResponse:
        # Réveille Kubuntu + décharge les LLM (capacité exclusive)
        disp = await dispatch("image")
        if not disp.get("ok"):
            return AgentResponse(
                request_id=req.request_id, agent="image",
                status=AgentStatus.error,
                content=(
                    "Le GPU (Kubuntu) est indisponible, impossible de générer une image.\n\n"
                    f"_{disp.get('error', 'GPU hors ligne')}._"
                ),
                tool_calls=[ToolCall(
                    tool="orchestration.dispatch", args={"capability": "image"},
                    result=ToolResult(ok=False, error=disp.get("error")),
                )],
            )

        prompt = self._to_prompt(req.message)
        result = await comfyui.generate(prompt)
        call = ToolCall(
            tool="comfyui.generate",
            args={"prompt": prompt, "checkpoint": disp.get("model")},
            result=ToolResult(ok=result is not None,
                              data=result if result else None,
                              error=None if result else "Génération échouée / ComfyUI injoignable"),
        )

        if not result:
            return AgentResponse(
                request_id=req.request_id, agent="image",
                status=AgentStatus.error,
                content="Kubuntu est joignable mais la génération a échoué. "
                        "Vérifie que le checkpoint SDXL est bien installé dans ComfyUI.",
                tool_calls=[call],
            )

        query = urlencode({
            "filename":  result["filename"],
            "subfolder": result["subfolder"],
            "type":      result["type"],
        })
        url = f"/api/images/view?{query}"
        # Enregistre dans la galerie durable
        from app.media import gallery
        await gallery.add_asset("image", result["filename"], result["subfolder"],
                                result["type"], prompt=prompt, base_url=disp.get("base_url"))
        return AgentResponse(
            request_id=req.request_id, agent="image",
            status=AgentStatus.ok,
            content=f"Image générée pour : *{prompt}* (seed {result['seed']}).",
            artifacts=[Artifact(kind="image", name=result["filename"], url=url)],
            tool_calls=[call],
        )
