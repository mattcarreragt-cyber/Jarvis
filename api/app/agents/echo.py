"""Agent echo — agent bidon pour valider le flux de bout en bout (étape 3).

Sera l'agent de conversation par défaut tant qu'aucun LLM n'est branché.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus


class EchoAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="echo",
            description="Agent de conversation par défaut. Répond quand aucun "
            "agent métier ne correspond.",
            keywords=[],  # pas de keywords : c'est le fallback
            default_permissions=[],
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        return AgentResponse(
            request_id=request.request_id,
            agent="echo",
            status=AgentStatus.ok,
            content=f"echo: {request.message}",
        )
