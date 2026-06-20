"""Tests Agent Unraid — stubs sans Docker socket ni fichiers Unraid."""

from unittest.mock import patch

from app.agents.unraid_agent import UnraidAgent
from app.contracts import AgentRequest, AgentStatus
from app.registry import registry
from app.router import route


def _stub_containers():
    from app.contracts import ToolResult
    return ToolResult(ok=True, data={
        "containers": [
            {"id": "a1", "name": "plex", "image": "plexinc/pms-docker:latest",
             "status": "running", "ports": []},
            {"id": "b2", "name": "sonarr", "image": "linuxserver/sonarr:latest",
             "status": "running", "ports": []},
            {"id": "c3", "name": "test_stopped", "image": "alpine:latest",
             "status": "exited", "ports": []},
        ],
        "total": 3,
    })


def _stub_docker_stats():
    from app.contracts import ToolResult
    return ToolResult(ok=True, data={"running": 2, "stopped": 1, "total": 3})


def _stub_array_status():
    from app.contracts import ToolResult
    return ToolResult(ok=True, data={
        "md_state": "STARTED", "md_num_disks": "6", "version": "6.12.6"
    })


async def test_unraid_agent_global_view():
    with (
        patch("app.agents.unraid_tools.docker_stats", _stub_docker_stats),
        patch("app.agents.unraid_tools.array_status", _stub_array_status),
    ):
        from app.agents import unraid_tools
        unraid_tools.HANDLERS["unraid.docker_stats"] = _stub_docker_stats
        unraid_tools.HANDLERS["unraid.array_status"] = _stub_array_status

        agent = UnraidAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r1", session_id="s1",
            intent="unraid", message="état du serveur",
        ))
    assert resp.status == AgentStatus.ok
    assert "Unraid" in resp.content
    assert "Conteneurs" in resp.content


async def test_unraid_agent_containers_view():
    with patch("app.agents.unraid_tools.containers", _stub_containers):
        from app.agents import unraid_tools
        unraid_tools.HANDLERS["unraid.containers"] = _stub_containers

        agent = UnraidAgent()
        resp = await agent.handle(AgentRequest(
            request_id="r2", session_id="s1",
            intent="unraid", message="liste les conteneurs docker",
        ))
    assert "plex" in resp.content
    assert "sonarr" in resp.content


def test_router_routes_unraid_keywords():
    for phrase in [
        "état des conteneurs unraid",
        "est-ce que plex tourne sur le serveur ?",
        "espace disque nas",
    ]:
        decision = route(phrase, registry)
        assert decision.agent == "unraid", f"phrase '{phrase}' → {decision.agent}"
