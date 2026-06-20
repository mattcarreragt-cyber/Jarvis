"""Construit et expose le registre global d'agents au démarrage."""

from __future__ import annotations

from app.agents.base import AgentRegistry
from app.agents.dev_agent import DevAgent
from app.agents.echo import EchoAgent
from app.agents.ha_agent import HomeAssistantAgent
from app.agents.marketing_agent import MarketingAgent
from app.agents.nextcloud_agent import NextcloudAgent
from app.agents.search_agent import SearchAgent
from app.agents.system_agent import SystemAgent
from app.agents.unraid_agent import UnraidAgent


def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(EchoAgent())
    registry.register(SystemAgent())
    registry.register(UnraidAgent())
    registry.register(HomeAssistantAgent())
    registry.register(SearchAgent())
    registry.register(MarketingAgent())
    registry.register(NextcloudAgent())
    registry.register(DevAgent())
    return registry


registry = build_registry()
