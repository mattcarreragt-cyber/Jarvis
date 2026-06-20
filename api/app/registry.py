"""Construit et expose le registre global d'agents au démarrage."""

from __future__ import annotations

from app.agents.base import AgentRegistry
from app.agents.echo import EchoAgent


def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(EchoAgent())
    # Les agents métier (system, marketing, ...) s'enregistrent ici.
    return registry


registry = build_registry()
