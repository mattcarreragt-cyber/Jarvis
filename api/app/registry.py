"""Construit et expose le registre global d'agents au démarrage."""

from __future__ import annotations

from app.agents.base import AgentRegistry
from app.agents.echo import EchoAgent
from app.agents.system_agent import SystemAgent
from app.agents.unraid_agent import UnraidAgent


def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(EchoAgent())
    registry.register(SystemAgent())
    registry.register(UnraidAgent())
    # Les autres agents (marketing, recherche, ...) s'enregistreront ici.
    return registry


registry = build_registry()
