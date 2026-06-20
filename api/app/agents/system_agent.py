"""Agent System — tranche verticale de référence (étape 4).

Collecte les métriques machine et renvoie un résumé markdown lisible.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.agents.system_tools import HANDLERS, SPECS
from app.contracts import (
    AgentRequest,
    AgentResponse,
    AgentSpec,
    AgentStatus,
    ToolCall,
)


class SystemAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="system",
            description="État et métriques de la machine locale : CPU, RAM, "
            "disque, uptime, processus.",
            keywords=[
                "cpu", "processeur", "ram", "mémoire", "memoire", "disque",
                "disk", "espace", "uptime", "charge", "machine", "système",
                "systeme", "processus",
            ],
            tools=SPECS,
            default_permissions=["system:read"],
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        # v1 : on collecte un panorama complet (lecture seule, peu coûteux).
        calls: list[ToolCall] = []
        for name in (
            "system.cpu_usage",
            "system.memory_usage",
            "system.disk_usage",
            "system.uptime",
        ):
            result = HANDLERS[name]()
            calls.append(ToolCall(tool=name, args={}, result=result))

        content = self._summarize(calls)
        return AgentResponse(
            request_id=request.request_id,
            agent="system",
            status=AgentStatus.ok,
            content=content,
            tool_calls=calls,
        )

    @staticmethod
    def _summarize(calls: list[ToolCall]) -> str:
        data = {c.tool: (c.result.data if c.result else {}) for c in calls}
        cpu = data.get("system.cpu_usage", {})
        mem = data.get("system.memory_usage", {})
        up = data.get("system.uptime", {})
        disks = data.get("system.disk_usage", {}).get("partitions", [])

        lines = ["## État de la machine", ""]
        lines.append(f"- **CPU** : {cpu.get('percent', '?')}% sur {cpu.get('cores', '?')} cœurs")
        lines.append(
            f"- **RAM** : {mem.get('used_gb', '?')} / {mem.get('total_gb', '?')} Go "
            f"({mem.get('percent', '?')}%)"
        )
        lines.append(
            f"- **Uptime** : {up.get('uptime_hours', '?')} h "
            f"(load {', '.join(map(str, up.get('load_avg', [])))})"
        )
        if disks:
            lines.append("- **Disques** :")
            for d in disks:
                lines.append(
                    f"  - `{d['mount']}` : {d['used_gb']} / {d['total_gb']} Go "
                    f"({d['percent']}%)"
                )
        return "\n".join(lines)
