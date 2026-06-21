"""Construit et expose le registre global d'agents au démarrage."""

from __future__ import annotations

from app.agents.base import AgentRegistry
from app.agents.agenda_agent import AgendaAgent
from app.agents.chat_agent import ChatAgent
from app.agents.dev_agent import DevAgent
from app.agents.echo import EchoAgent
from app.agents.ha_agent import HomeAssistantAgent
from app.agents.image_agent import ImageAgent
from app.agents.marketing_agent import MarketingAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.nextcloud_agent import NextcloudAgent
from app.agents.search_agent import SearchAgent
from app.agents.system_agent import SystemAgent
from app.agents.unraid_agent import UnraidAgent
from app.agents.video_agent import VideoAgent


def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(EchoAgent())
    registry.register(ChatAgent())
    registry.register(SystemAgent())
    registry.register(UnraidAgent())
    registry.register(HomeAssistantAgent())
    registry.register(SearchAgent())
    registry.register(MarketingAgent())
    registry.register(NextcloudAgent())
    registry.register(MemoryAgent())
    registry.register(AgendaAgent())
    registry.register(ImageAgent())
    registry.register(VideoAgent())
    registry.register(DevAgent())
    return registry


registry = build_registry()
