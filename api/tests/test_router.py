"""Tests du router à règles + flux echo (critère 'fini' étape 3)."""

import pytest

from app.agents.base import Agent, AgentRegistry
from app.agents.echo import EchoAgent
from app.contracts import AgentRequest, AgentResponse, AgentSpec
from app.router import route


class _SystemStub(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="system",
            description="Machine locale",
            keywords=["cpu", "ram", "disque", "machine"],
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        return AgentResponse(request_id=request.request_id, agent="system")


@pytest.fixture
def registry() -> AgentRegistry:
    r = AgentRegistry()
    r.register(EchoAgent())
    r.register(_SystemStub())
    return r


def test_keyword_match_routes_to_agent(registry):
    decision = route("quel est l'usage du CPU ?", registry)
    assert decision.agent == "system"
    assert decision.method == "rules"
    assert decision.score >= 1.0


def test_no_match_falls_back_to_echo(registry):
    decision = route("raconte-moi une blague", registry)
    assert decision.agent == "echo"


def test_force_agent_bypasses_rules(registry):
    decision = route("usage du cpu", registry, force_agent="echo")
    assert decision.agent == "echo"
    assert decision.method == "forced"


@pytest.mark.asyncio
async def test_echo_agent_roundtrip():
    agent = EchoAgent()
    resp = await agent.handle(
        AgentRequest(request_id="r1", session_id="s1", intent="echo", message="ping")
    )
    assert resp.content == "echo: ping"
    assert resp.agent == "echo"
