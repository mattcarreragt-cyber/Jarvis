"""Construit et expose le registre global d'agents au démarrage."""

from __future__ import annotations

from app.agents.base import AgentRegistry
from app.agents.echo import EchoAgent
from app.agents.system_agent import SystemAgent


def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(EchoAgent())
    registry.register(SystemAgent())
    # Les autres agents métier (marketing, unraid, ...) s'enregistrent ici.
    return registry


registry = build_registry()
