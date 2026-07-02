"""Tests Agent Home Assistant — exécution directe (sans confirmation)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents import ha_tools
from app.agents.ha_agent import HomeAssistantAgent
from app.contracts import AgentRequest, AgentStatus, ToolResult
from app.registry import registry
from app.router import route

_STATES = [
    {"entity_id": "light.salon", "state": "on",  "friendly_name": "Lumière salon"},
    {"entity_id": "light.chambre", "state": "off", "friendly_name": "Lumière chambre"},
    {"entity_id": "sensor.temp_salon", "state": "21.5", "friendly_name": "Temp salon"},
]

_OK = ToolResult(ok=True, data={"called": "x"})


@pytest.fixture(autouse=True)
def _clear_caches():
    ha_tools._reset_caches()
    yield
    ha_tools._reset_caches()


def _req(message: str, rid: str = "r1") -> AgentRequest:
    return AgentRequest(request_id=rid, session_id="s1",
                        intent="home_assistant", message=message)


async def test_ha_read_states():
    with patch("app.agents.ha_agent.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )):
        resp = await HomeAssistantAgent().handle(_req("état des lumières"))
    assert resp.status == AgentStatus.ok
    assert "Lumière salon" in resp.content


async def test_ha_write_executes_directly():
    """« allume light.salon » → turn_on appelé immédiatement, pas de confirmation."""
    with patch("app.agents.ha_agent.turn_on", new=AsyncMock(return_value=_OK)) as m:
        resp = await HomeAssistantAgent().handle(_req("allume light.salon"))
    assert resp.status == AgentStatus.ok
    assert resp.confirmation is None
    m.assert_awaited_once_with("light.salon")


async def test_ha_off_executes_directly():
    with patch("app.agents.ha_agent.turn_off", new=AsyncMock(return_value=_OK)) as m:
        resp = await HomeAssistantAgent().handle(_req("éteins light.chambre"))
    assert resp.status == AgentStatus.ok
    m.assert_awaited_once_with("light.chambre")


async def test_ha_resolve_by_friendly_name():
    """« allume la lumière du salon » (sans entity_id) → résolu par friendly_name."""
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value={}), \
         patch("app.agents.ha_agent.turn_on", new=AsyncMock(return_value=_OK)) as m:
        resp = await HomeAssistantAgent().handle(_req("allume la lumière du salon"))
    assert resp.status == AgentStatus.ok
    m.assert_awaited_once_with("light.salon")


async def test_ha_resolve_by_alias_multi():
    """Un alias multi-entités → UN SEUL appel de service avec la liste."""
    aliases = {"aliases": {"luminaires salon": ["light.salon", "light.chambre"]}}
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value=aliases), \
         patch("app.agents.ha_agent.turn_off", new=AsyncMock(return_value=_OK)) as m:
        resp = await HomeAssistantAgent().handle(_req("éteins les luminaires du salon"))
    assert resp.status == AgentStatus.ok
    m.assert_awaited_once_with(["light.salon", "light.chambre"])


async def test_ha_resolve_not_found_is_helpful():
    """Cible introuvable → message d'aide (pas un dump d'entités)."""
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value={}):
        resp = await HomeAssistantAgent().handle(_req("allume le truc inexistant zzz"))
    assert resp.status == AgentStatus.ok
    assert "ha_aliases.yaml" in resp.content


# ─── Garde-fous : les questions ne déclenchent JAMAIS d'action ───────────────

@pytest.mark.parametrize("question", [
    "le four est-il éteint ?",
    "la lumière du salon est éteinte ?",
    "quelles lumières sont éteintes",
    "est-ce qu'on a du chauffage ?",
    "quelle était la température à 15 heures dans le salon ?",
])
async def test_ha_questions_never_write(question):
    with patch("app.agents.ha_agent.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_agent.turn_on", new=AsyncMock(return_value=_OK)) as on, \
         patch("app.agents.ha_agent.turn_off", new=AsyncMock(return_value=_OK)) as off, \
         patch("app.agents.ha_agent.set_temperature", new=AsyncMock(return_value=_OK)) as st:
        resp = await HomeAssistantAgent().handle(_req(question))
    on.assert_not_awaited()
    off.assert_not_awaited()
    st.assert_not_awaited()
    assert resp.status == AgentStatus.ok


async def test_ha_participles_do_not_trigger_write():
    """« liste les lumières allumées » : participe ≠ impératif → lecture."""
    with patch("app.agents.ha_agent.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_agent.turn_on", new=AsyncMock(return_value=_OK)) as on:
        resp = await HomeAssistantAgent().handle(_req("liste les lumières allumées"))
    on.assert_not_awaited()
    assert resp.status == AgentStatus.ok


async def test_ha_alias_singular_plural_equivalence():
    """« volet chambre » (alias) matche « ferme les VOLETS de la chambre »."""
    aliases = {"aliases": {"volet chambre": "cover.chambre"}}
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value=aliases), \
         patch("app.agents.ha_agent.turn_off", new=AsyncMock(return_value=_OK)) as m:
        resp = await HomeAssistantAgent().handle(_req("ferme les volets de la chambre"))
    assert resp.status == AgentStatus.ok
    m.assert_awaited_once_with("cover.chambre")


async def test_ha_on_at_end_of_message():
    """« Luminaires salon ON » (le cas d'usage d'origine) → allume."""
    aliases = {"aliases": {"luminaires salon": ["light.salon"]}}
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value=aliases), \
         patch("app.agents.ha_agent.turn_on", new=AsyncMock(return_value=_OK)) as m:
        resp = await HomeAssistantAgent().handle(_req("Luminaires salon ON"))
    assert resp.status == AgentStatus.ok
    m.assert_awaited_once_with("light.salon")


# ─── Consigne de température ─────────────────────────────────────────────────

async def test_ha_set_temperature_natural_phrase():
    """« mets le chauffage à 21 » → set_temperature(climate, 21.0)."""
    aliases = {"aliases": {"chauffage": "climate.thermostat"}}
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value=aliases), \
         patch("app.agents.ha_agent.set_temperature", new=AsyncMock(return_value=_OK)) as m:
        resp = await HomeAssistantAgent().handle(_req("mets le chauffage à 21"))
    assert resp.status == AgentStatus.ok
    m.assert_awaited_once_with("climate.thermostat", 21.0)


async def test_ha_set_temperature_degree_symbol():
    """« règle le chauffage sur 21° » → le symbole ° sans C est reconnu."""
    aliases = {"aliases": {"chauffage": "climate.thermostat"}}
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value=aliases), \
         patch("app.agents.ha_agent.set_temperature", new=AsyncMock(return_value=_OK)) as m:
        resp = await HomeAssistantAgent().handle(_req("règle le chauffage sur 21°"))
    assert resp.status == AgentStatus.ok
    m.assert_awaited_once_with("climate.thermostat", 21.0)


async def test_ha_set_temperature_water_heater():
    """« règle l'eau chaude à 30 degrés » → service water_heater, pas climate."""
    aliases = {"aliases": {"eau chaude": "water_heater.eau_chaude"}}
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value=aliases), \
         patch("app.agents.ha_agent.set_temperature", new=AsyncMock(return_value=_OK)) as m:
        resp = await HomeAssistantAgent().handle(_req("règle l'eau chaude à 30 degrés"))
    assert resp.status == AgentStatus.ok
    m.assert_awaited_once_with("water_heater.eau_chaude", 30.0)


async def test_ha_temperature_on_non_climate_falls_through():
    """« mets le salon à 21 » : résout une lumière → PAS de set_temperature."""
    with patch("app.agents.ha_tools.get_states", new=AsyncMock(
        return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
    )), patch("app.agents.ha_tools._load_aliases", return_value={}), \
         patch("app.agents.ha_agent.get_states", new=AsyncMock(
            return_value=ToolResult(ok=True, data={"states": _STATES, "total": 3})
         )), \
         patch("app.agents.ha_agent.set_temperature", new=AsyncMock(return_value=_OK)) as st:
        resp = await HomeAssistantAgent().handle(_req("mets le salon à 21"))
    st.assert_not_awaited()
    assert resp.status == AgentStatus.ok


def test_router_routes_domotique():
    for phrase in ["état des lumières maison", "allume la lumière salon",
                   "chauffage température"]:
        d = route(phrase, registry)
        assert d.agent == "home_assistant", f"'{phrase}' → {d.agent}"
