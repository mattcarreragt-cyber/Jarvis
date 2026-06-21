"""Agent Bureau distant — réveille Kubuntu (WoL) et prépare le streaming Moonlight/Sunshine."""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult
from app.remote import stream

_STATUS = re.compile(r"\b(statut|état|etat|est[-\s]?(?:ce|il)\s+up|dispo)\b", re.I)


class RemoteAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="bureau",
            description="Bureau distant / streaming : réveille Kubuntu (Wake-on-LAN) "
                        "et vérifie Sunshine pour se connecter avec Moonlight.",
            keywords=[
                "moonlight", "sunshine", "streaming", "stream", "bureau distant",
                "réveille", "reveille", "réveiller", "wake-on-lan", "wol",
                "allume le pc", "réveille kubuntu", "lance le streaming", "gaming",
            ],
            default_permissions=["remote:wake"],
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        # Statut seul
        if _STATUS.search(req.message) and not re.search(r"\b(réveille|reveille|allume|lance|démarre|demarre)\b", req.message, re.I):
            up = await stream.is_sunshine_up()
            host = stream.kubuntu_host()
            call = ToolCall(tool="remote.status", args={},
                            result=ToolResult(ok=True, data={"sunshine_up": up}))
            txt = (f"🟢 Sunshine est **en ligne** sur `{host}` — connecte-toi via Moonlight."
                   if up else
                   f"🔴 Sunshine ne répond pas sur `{host}`. Dis « réveille kubuntu » pour le démarrer.")
            return self._r(req, txt, call)

        # Réveil + attente
        res = await stream.wake_and_wait()
        call = ToolCall(tool="remote.wake_and_wait", args={},
                        result=ToolResult(ok=res["sunshine_up"], data=res))
        if res["sunshine_up"]:
            txt = (f"✅ Kubuntu est réveillé et **Sunshine est prêt** sur `{res['host']}`.\n\n"
                   f"Ouvre **Moonlight** → l'hôte devrait apparaître (sinon ajoute `{res['host']}`) "
                   f"→ lance le streaming.")
        elif not res.get("mac_set", True):
            txt = ("⚠️ Adresse MAC de Kubuntu non configurée (`KUBUNTU_MAC`), impossible "
                   "d'envoyer le Wake-on-LAN. Renseigne-la dans le `.env`.")
        else:
            txt = (f"📡 Magic packet envoyé à Kubuntu, mais Sunshine n'a pas répondu dans le "
                   f"délai sur `{res['host']}:{res['port']}`.\n\n"
                   "Vérifie : la machine démarre bien, Sunshine est lancé au démarrage, et la "
                   "session unique est ouverte (voir SUNSHINE_MOONLIGHT.md).")
        return self._r(req, txt, call,
                       status=AgentStatus.ok if res["sunshine_up"] else AgentStatus.error)

    @staticmethod
    def _r(req, content, call, status=AgentStatus.ok):
        return AgentResponse(request_id=req.request_id, agent="bureau", status=status,
                             content=content, tool_calls=[call])
