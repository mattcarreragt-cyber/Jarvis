"""Agent Unraid — monitoring et état du serveur Unraid.

V1 : lecture seule (containers, array, disques). Les actions write arrivent en v2
avec confirmation obligatoire (rule de la spec : ne jamais casser l'existant).
"""

from __future__ import annotations

from app.agents.base import Agent
from app.agents.unraid_tools import HANDLERS, SPECS
from app.contracts import (
    AgentRequest,
    AgentResponse,
    AgentSpec,
    AgentStatus,
    ToolCall,
)


class UnraidAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="unraid",
            description="État du serveur Unraid : conteneurs Docker, array, disques.",
            keywords=[
                "unraid", "conteneur", "container", "docker", "array",
                "nas", "serveur", "server", "plex", "démarrer", "arrêter",
                "disque", "disk", "stockage", "espace", "plugins",
            ],
            tools=SPECS,
            default_permissions=["unraid:read"],
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        msg = request.message.lower()

        # Sélection des outils selon la demande
        tools_to_run: list[str] = []

        if any(w in msg for w in ["conteneur", "container", "docker", "plex", "service"]):
            tools_to_run.append("unraid.containers")
        if any(w in msg for w in ["array", "parité", "disque", "stockage", "disques"]):
            tools_to_run += ["unraid.array_status", "unraid.disks_status"]
        if not tools_to_run:
            # Vue globale par défaut
            tools_to_run = ["unraid.docker_stats", "unraid.array_status"]

        calls: list[ToolCall] = []
        for name in tools_to_run:
            result = HANDLERS[name]()
            calls.append(ToolCall(tool=name, args={}, result=result))

        content = self._summarize(calls)
        return AgentResponse(
            request_id=request.request_id,
            agent="unraid",
            status=AgentStatus.ok,
            content=content,
            tool_calls=calls,
        )

    @staticmethod
    def _summarize(calls: list[ToolCall]) -> str:
        data = {c.tool: c.result for c in calls}
        lines = ["## État Unraid", ""]

        # Docker global
        if "unraid.docker_stats" in data:
            r = data["unraid.docker_stats"]
            if r and r.ok and r.data:
                d = r.data
                lines.append(
                    f"- **Conteneurs** : {d['running']} en cours / "
                    f"{d['total']} total ({d['stopped']} stoppés)"
                )

        # Array
        if "unraid.array_status" in data:
            r = data["unraid.array_status"]
            if r and r.ok and r.data:
                d = r.data
                lines.append(
                    f"- **Array** : {d['md_state']} "
                    f"({d['md_num_disks']} disques) — Unraid {d['version']}"
                )
            elif r and not r.ok:
                lines.append(f"- **Array** : {r.error}")

        # Conteneurs détaillés
        if "unraid.containers" in data:
            r = data["unraid.containers"]
            if r and r.ok and r.data:
                running = [c for c in r.data["containers"] if c["status"] == "running"]
                stopped = [c for c in r.data["containers"] if c["status"] != "running"]
                if running:
                    lines += ["", "**En cours :**"]
                    for c in running[:10]:
                        lines.append(f"  - `{c['name']}` ({c['image'].split(':')[0]})")
                if stopped:
                    lines += ["", "**Stoppés :**"]
                    for c in stopped[:5]:
                        lines.append(f"  - `{c['name']}` — {c['status']}")

        # Disques
        if "unraid.disks_status" in data:
            r = data["unraid.disks_status"]
            if r and r.ok and r.data:
                lines += ["", "**Disques :**"]
                for d in r.data["disks"][:8]:
                    temp = f"{d['temp']}°C" if d["temp"] not in ("?", "") else "?"
                    lines.append(
                        f"  - `{d['name']}` ({d['device']}) — {d['status']} — {temp}"
                    )
            elif r and not r.ok:
                lines.append(f"\n- **Disques** : {r.error}")

        return "\n".join(lines)
