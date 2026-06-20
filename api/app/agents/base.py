"""Base commune des agents et registre."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.contracts import AgentRequest, AgentResponse, AgentSpec


class Agent(ABC):
    """Tout agent expose un AgentSpec statique et une méthode handle()."""

    @property
    @abstractmethod
    def spec(self) -> AgentSpec: ...

    @abstractmethod
    async def handle(self, request: AgentRequest) -> AgentResponse: ...


class AgentRegistry:
    """Conserve les agents enregistrés et expose leurs specs au Router."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.spec.name] = agent

    def get(self, name: str) -> Agent | None:
        return self._agents.get(name)

    def all(self) -> list[Agent]:
        return list(self._agents.values())

    def specs(self) -> list[AgentSpec]:
        return [a.spec for a in self._agents.values()]
