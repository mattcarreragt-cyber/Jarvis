"""Tests Agent Home Assistant."""

from unittest.mock import AsyncMock, patch

from app.agents.ha_agent import HomeAssistantAgent
from app.contracts import AgentRequest, AgentStatus
from app.registry import registry
from app.router import route

_STATES = [
    {"entity_id": "light.salon", "state": "on",  "friendly_name": "Lumière salon"},
    {"entity_id": "light.chambre", "state": "off", "friendly_name": "Lumière chambre"},
    {"entity_id": "sensor.temp_salon", "state": "21.5", "friendly_name": "Temp salon"},
]


async def test_ha_read_states():
    from app.contracts import ToolResult
    with patch("app.agents.ha_agent.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )):
        agent = HomeAssistantAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r1", session_id="s1",
            intent="home_assistant", message="état des lumières",
        ))
    assert resp.status == AgentStatus.ok
    assert "Lumière salon" in resp.content


async def test_ha_write_needs_confirmation():
    agent = HomeAssistantAgent()
    resp = await agent.handle(AgentRequest(
        request_id="r2", session_id="s1",
        intent="home_assistant",
        message="allume light.salon",
    ))
    assert resp.status == AgentStatus.needs_confirmation
    assert resp.confirmation is not None
    assert resp.confirmation.tool == "ha.turn_on"
    assert resp.confirmation.args["entity_id"] == "light.salon"


async def test_ha_off_needs_confirmation():
    agent = HomeAssistantAgent()
    resp = await agent.handle(AgentRequest(
        request_id="r3", session_id="s1",
        intent="home_assistant",
        message="éteins light.chambre",
    ))
    assert resp.status == AgentStatus.needs_confirmation
    assert resp.confirmation.tool == "ha.turn_off"


async def test_ha_resolve_by_friendly_name():
    """« allume la lumière du salon » (sans entity_id) → résolu par friendly_name."""
    from app.contracts import ToolResult
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value={}):
        agent = HomeAssistantAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r4", session_id="s1", intent="home_assistant",
            message="allume la lumière du salon",
        ))
    assert resp.status == AgentStatus.needs_confirmation
    assert resp.confirmation.tool == "ha.turn_on"
    assert resp.confirmation.args["entity_id"] == "light.salon"


async def test_ha_resolve_by_alias_multi():
    """Un alias peut viser plusieurs entités à la fois."""
    from app.contracts import ToolResult
    aliases = {"aliases": {"luminaires salon": ["light.salon", "light.chambre"]}}
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value=aliases):
        agent = HomeAssistantAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r5", session_id="s1", intent="home_assistant",
            message="éteins les luminaires du salon",
        ))
    assert resp.status == AgentStatus.needs_confirmation
    assert resp.confirmation.tool == "ha.turn_off"
    assert resp.confirmation.args["entity_id"] == ["light.salon", "light.chambre"]


async def test_ha_resolve_not_found_is_helpful():
    """Cible introuvable → message d'aide (pas un dump d'entités)."""
    from app.contracts import ToolResult
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value={}):
        agent = HomeAssistantAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r6", session_id="s1", intent="home_assistant",
            message="allume le truc inexistant zzz",
        ))
    assert resp.status == AgentStatus.ok
    assert "ha_aliases.yaml" in resp.content


def test_router_routes_domotique():
    for phrase in ["état des lumières maison", "allume la lumière salon",
                   "chauffage température"]:
        d = route(phrase, registry)
        assert d.agent == "home_assistant", f"'{phrase}' → {d.agent}"
