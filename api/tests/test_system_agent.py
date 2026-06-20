"""Tests Agent System — critère 'fini' étape 4 (tranche verticale)."""

from app.agents.system_agent import SystemAgent
from app.agents.system_tools import HANDLERS
from app.contracts import AgentRequest, AgentStatus
from app.registry import registry
from app.router import route


def test_tools_return_ok():
    for name, handler in HANDLERS.items():
        result = handler()
        assert result.ok is True, name
        assert result.data is not None, name


async def test_system_agent_produces_summary():
    agent = SystemAgent()
    resp = await agent.handle(
        AgentRequest(
            request_id="r1", session_id="s1", intent="system",
            message="quel est l'état de la machine ?",
        )
    )
    assert resp.status == AgentStatus.ok
    assert resp.agent == "system"
    assert "État de la machine" in resp.content
    assert "CPU" in resp.content and "RAM" in resp.content
    # traçabilité : les outils appelés sont présents
    assert any(c.tool == "system.cpu_usage" for c in resp.tool_calls)


def test_router_routes_machine_question_to_system():
    decision = route("quel est l'état de la machine ?", registry)
    assert decision.agent == "system"
    assert decision.method == "rules"


def test_router_cpu_keyword():
    decision = route("montre-moi l'usage du CPU et de la RAM", registry)
    assert decision.agent == "system"
