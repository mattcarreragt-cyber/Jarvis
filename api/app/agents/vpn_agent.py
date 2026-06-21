"""Agent VPN — statut et contrôle Mullvad."""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult
from app.vpn import mullvad

_CONNECT = re.compile(r"\b(connecte|active|lance|allume)\b", re.I)
_DISCONNECT = re.compile(r"\b(déconnecte|deconnecte|coupe|désactive|desactive|arrête|arrete)\b", re.I)
_LOCATION = re.compile(r"\b(?:pays|location|relais?|serveur)\s+([a-z]{2})\b", re.I)


class VpnAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="vpn",
            description="Statut et contrôle du VPN Mullvad : vérifier la protection, "
                        "connecter / déconnecter, changer de pays.",
            keywords=[
                "vpn", "mullvad", "anonyme", "anonymat", "suis-je protégé",
                "mon ip", "protégé", "protege", "tunnel",
            ],
            default_permissions=["vpn:read"],
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        msg = req.message

        # Contrôle (connect/disconnect/location)
        loc = _LOCATION.search(msg)
        if loc:
            res = await mullvad.control("location", loc.group(1).lower())
            return self._ctl(req, res, f"VPN → pays {loc.group(1).upper()}")
        if _DISCONNECT.search(msg):
            res = await mullvad.control("disconnect")
            return self._ctl(req, res, "VPN déconnecté")
        if _CONNECT.search(msg) and re.search(r"\b(vpn|mullvad)\b", msg, re.I):
            res = await mullvad.control("connect")
            return self._ctl(req, res, "VPN connecté")

        # Statut : SSH (précis pour l'hôte) sinon HTTP (sortie JARVIS)
        ssh = await mullvad.ssh_status()
        if ssh:
            return self._r(req, f"## Statut VPN (Mullvad CLI)\n```\n{ssh}\n```",
                           ToolCall(tool="vpn.ssh_status", args={}, result=ToolResult(ok=True)))

        data = await mullvad.http_status()
        call = ToolCall(tool="vpn.http_status", args={}, result=ToolResult(ok=data is not None, data=data))
        if data is None:
            return self._r(req, "Impossible de vérifier le statut VPN (réseau indisponible).",
                           call, status=AgentStatus.error)
        protected = data.get("mullvad_exit_ip", False)
        icon = "🟢" if protected else "🔴"
        loc_txt = f"{data.get('city', '?')}, {data.get('country', '?')}"
        lines = [f"{icon} **{'Protégé par Mullvad' if protected else 'NON protégé'}** "
                 f"_(vu depuis le serveur JARVIS)_",
                 f"- IP de sortie : `{data.get('ip', '?')}`",
                 f"- Localisation : {loc_txt}",
                 f"- Organisation : {data.get('organization', '?')}"]
        if not protected:
            lines.append("\n_Ceci reflète la sortie réseau d'Unraid. Pour un autre hôte, "
                         "configure MULLVAD_SSH_HOST._")
        return self._r(req, "\n".join(lines), call)

    def _ctl(self, req, res, label):
        if res.get("ok"):
            return self._r(req, f"✅ {label}.",
                           ToolCall(tool="vpn.control", args={}, result=ToolResult(ok=True)))
        return self._r(req, f"⚠️ {label} impossible : {res.get('error')}",
                       ToolCall(tool="vpn.control", args={}, result=ToolResult(ok=False, error=res.get('error'))),
                       status=AgentStatus.error)

    @staticmethod
    def _r(req, content, call, status=AgentStatus.ok):
        return AgentResponse(request_id=req.request_id, agent="vpn", status=status,
                             content=content, tool_calls=[call])
