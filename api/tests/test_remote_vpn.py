"""Tests agents Bureau distant (streaming/WoL) et VPN Mullvad (mocks)."""

from unittest.mock import AsyncMock, patch

from app.agents.remote_agent import RemoteAgent
from app.agents.vpn_agent import VpnAgent
from app.contracts import AgentRequest, AgentStatus
from app.registry import registry
from app.router import route


def _req(agent, msg):
    return AgentRequest(request_id="r1", session_id="s1", intent=agent, message=msg)


# ─── Bureau distant ──────────────────────────────────────────────────────────

async def test_remote_wake_success():
    res = {"woke": True, "sunshine_up": True, "host": "10.0.0.2", "port": 47989}
    with patch("app.agents.remote_agent.stream.wake_and_wait", new=AsyncMock(return_value=res)):
        resp = await RemoteAgent().handle(_req("bureau", "réveille kubuntu pour le streaming"))
    assert resp.status == AgentStatus.ok
    assert "Sunshine est prêt" in resp.content
    assert "Moonlight" in resp.content


async def test_remote_wake_no_mac():
    res = {"woke": False, "sunshine_up": False, "host": "kubuntu", "port": 47989, "mac_set": False}
    with patch("app.agents.remote_agent.stream.wake_and_wait", new=AsyncMock(return_value=res)):
        resp = await RemoteAgent().handle(_req("bureau", "réveille kubuntu"))
    assert resp.status == AgentStatus.error
    assert "MAC" in resp.content


async def test_remote_status_only():
    with patch("app.agents.remote_agent.stream.is_sunshine_up", new=AsyncMock(return_value=True)), \
         patch("app.agents.remote_agent.stream.kubuntu_host", return_value="10.0.0.2"):
        resp = await RemoteAgent().handle(_req("bureau", "statut du streaming sunshine ?"))
    assert "en ligne" in resp.content.lower()


def test_router_remote_keywords():
    for p in ["réveille kubuntu", "lance moonlight", "statut sunshine"]:
        assert route(p, registry).agent == "bureau", p


# ─── VPN Mullvad ─────────────────────────────────────────────────────────────

async def test_vpn_status_http_protected():
    data = {"mullvad_exit_ip": True, "ip": "1.2.3.4", "city": "Paris",
            "country": "France", "organization": "Mullvad VPN"}
    with patch("app.agents.vpn_agent.mullvad.ssh_status", new=AsyncMock(return_value=None)), \
         patch("app.agents.vpn_agent.mullvad.http_status", new=AsyncMock(return_value=data)):
        resp = await VpnAgent().handle(_req("vpn", "suis-je protégé par le vpn ?"))
    assert "Protégé" in resp.content
    assert "1.2.3.4" in resp.content


async def test_vpn_status_not_protected():
    data = {"mullvad_exit_ip": False, "ip": "9.9.9.9", "city": "x", "country": "y",
            "organization": "ISP"}
    with patch("app.agents.vpn_agent.mullvad.ssh_status", new=AsyncMock(return_value=None)), \
         patch("app.agents.vpn_agent.mullvad.http_status", new=AsyncMock(return_value=data)):
        resp = await VpnAgent().handle(_req("vpn", "statut vpn"))
    assert "NON protégé" in resp.content


async def test_vpn_connect_control():
    with patch("app.agents.vpn_agent.mullvad.control",
               new=AsyncMock(return_value={"ok": True, "output": "connected"})) as ctl:
        resp = await VpnAgent().handle(_req("vpn", "connecte le vpn mullvad"))
    assert resp.status == AgentStatus.ok
    ctl.assert_awaited_once()


async def test_vpn_location_change():
    with patch("app.agents.vpn_agent.mullvad.control",
               new=AsyncMock(return_value={"ok": True})) as ctl:
        resp = await VpnAgent().handle(_req("vpn", "vpn pays se"))
    assert "SE" in resp.content
    assert ctl.call_args.args[0] == "location"


def test_router_vpn_keywords():
    for p in ["statut du vpn", "suis-je protégé", "mullvad connecte"]:
        assert route(p, registry).agent == "vpn", p
