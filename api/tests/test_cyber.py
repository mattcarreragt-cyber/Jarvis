"""Tests module cybersécurité — checks d'audit + agent (runner mocké, sans SSH)."""

from unittest.mock import AsyncMock, patch

from app.agents.cyber_agent import CyberAgent
from app.contracts import AgentRequest, AgentStatus
from app.cyber import audit


def _runner(responses: dict):
    """Fabrique un run(cmd) qui renvoie une sortie selon un mot-clé présent dans cmd."""
    async def run(cmd, timeout=120):
        for key, val in responses.items():
            if key in cmd:
                return val
        return ""
    return run


async def test_audit_detects_root_login_and_uid0():
    run = _runner({
        "sshd": "permitrootlogin yes\npasswordauthentication yes",
        "UID": "",  # awk uid0 -> handled below
        "($3==0)": "root\nbackdoor",
        "shadow": "",
        "ufw": "Status: active",
        "upgrade": "0",
    })
    res = await audit.run_audit({"label": "x"}, runner=run)
    assert res["ok"] is True
    titles = [f["title"] for f in res["findings"]]
    assert any("root" in t.lower() for t in titles)         # PermitRootLogin
    assert any("UID 0" in t for t in titles)                # compte UID 0
    assert res["summary"]["critical"] >= 1


async def test_audit_clean_host():
    run = _runner({
        "sshd": "permitrootlogin no\npasswordauthentication no",
        "($3==0)": "root",
        "shadow": "",
        "ufw": "Status: active",
        "upgrade": "0",
        "ss -tlnH": "",
        "docker": "",
        "auth.log": "0",
        "-perm -4000": "",
    })
    res = await audit.run_audit({"label": "x"}, runner=run)
    assert res["ok"] is True
    assert res["summary"]["critical"] == 0
    assert res["summary"]["high"] == 0


async def test_audit_connection_failure():
    with patch("app.cyber.audit.ssh.make_runner", new=AsyncMock(side_effect=OSError("refused"))):
        res = await audit.run_audit({"label": "x", "hostname": "h", "username": "u"})
    assert res["ok"] is False
    assert "SSH" in res["error"]


async def test_agent_lists_hosts():
    with patch("app.agents.cyber_agent.store.list_hosts",
               new=AsyncMock(return_value=[{"label": "unraid", "hostname": "10.0.0.1",
                                            "port": 22, "username": "root"}])):
        resp = await CyberAgent().handle(AgentRequest(
            request_id="c1", session_id="s1", intent="cyber", message="mes machines"))
    assert "unraid" in resp.content


async def test_agent_audits_named_host():
    hosts = [{"id": "h1", "label": "unraid", "hostname": "10.0.0.1", "port": 22, "username": "root"}]
    audit_res = {"ok": True, "findings": [
        {"check": "sshd", "severity": "high", "title": "Connexion SSH root autorisée",
         "detail": "PermitRootLogin yes", "recommendation": "Désactiver", "remediation": "sed ..."}],
        "summary": {"critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0}}
    with patch("app.agents.cyber_agent.store.list_hosts", new=AsyncMock(return_value=hosts)), \
         patch("app.agents.cyber_agent.audit.run_audit", new=AsyncMock(return_value=audit_res)), \
         patch("app.agents.cyber_agent.store.save_findings", new=AsyncMock()):
        resp = await CyberAgent().handle(AgentRequest(
            request_id="c2", session_id="s1", intent="cyber", message="audite unraid"))
    assert resp.status == AgentStatus.ok
    assert "Audit sécurité" in resp.content
    assert "root" in resp.content.lower()
    assert "appliqués automatiquement" in resp.content


async def test_agent_no_host_match():
    with patch("app.agents.cyber_agent.store.list_hosts", new=AsyncMock(return_value=[])):
        resp = await CyberAgent().handle(AgentRequest(
            request_id="c3", session_id="s1", intent="cyber", message="audite le serveur"))
    assert "précise l'hôte" in resp.content.lower() or "aucun" in resp.content.lower()


def test_router_cyber_keywords():
    from app.registry import registry
    from app.router import route
    for p in ["audite la sécurité de unraid", "quelles failles", "durcis le pare-feu"]:
        assert route(p, registry).agent == "cyber", p
