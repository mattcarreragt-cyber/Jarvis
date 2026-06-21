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


def test_nmap_parse_detects_risky_services():
    from app.cyber import nmap_scan
    grep = ("Host: 10.0.0.1 ()\tStatus: Up\n"
            "Host: 10.0.0.1 ()\tPorts: 22/open/tcp//ssh//OpenSSH/, "
            "23/open/tcp//telnet///, 6379/open/tcp//redis///\tIgnored\n")
    f = nmap_scan._parse_grepable(grep)
    titles = " ".join(x["title"] for x in f)
    assert "Telnet" in titles
    assert "Redis" in titles
    # telnet = critical
    assert any(x["severity"] == "critical" for x in f)


def test_nmap_parse_empty():
    from app.cyber import nmap_scan
    assert nmap_scan._parse_grepable("Host: x Status: Up") == []


def test_compute_score_and_grade():
    crit = [{"severity": "critical"}]
    assert audit.compute_score(crit) == (70, "C")
    clean = []
    assert audit.compute_score(clean) == (100, "A")
    many = [{"severity": "critical"}, {"severity": "high"}, {"severity": "high"}]
    score, grade = audit.compute_score(many)   # 100-30-15-15 = 40
    assert score == 40 and grade == "D"


async def test_lynis_not_installed_finding():
    run = _runner({"lynis": "__NOLYNIS__"})
    f = await audit._check_lynis(run)
    assert f and f[0].severity == "info"
    assert "lynis" in f[0].title.lower()


async def test_lynis_hardening_index_parsed():
    run = _runner({"lynis": "Hardening index : 45 [######      ]\nWarning: weak config"})
    f = await audit._check_lynis(run)
    titles = " ".join(x.title for x in f)
    assert "45/100" in titles
    assert any(x.severity == "high" for x in f)   # index < 50


async def test_audit_includes_score():
    run = _runner({"($3==0)": "root", "ufw": "Status: active", "upgrade": "0",
                   "lynis": "__NOLYNIS__"})
    res = await audit.run_audit({"label": "x"}, runner=run, with_nmap=False)
    assert "score" in res and "grade" in res
    assert 0 <= res["score"] <= 100


# ─── Rootkits ────────────────────────────────────────────────────────────────

async def test_rootkit_no_scanner():
    run = _runner({"command -v rkhunter": "__NORK__"})
    f = await audit._check_rootkits(run)
    assert f and f[0].severity == "info"


async def test_rootkit_infected_critical():
    run = _runner({"command -v rkhunter": "/bin/ls INFECTED\nWarning: suspicious file"})
    f = await audit._check_rootkits(run)
    sev = [x.severity for x in f]
    assert "critical" in sev
    assert "medium" in sev   # le warning


# ─── CVE (OSV) ───────────────────────────────────────────────────────────────

def test_cve_ecosystem_detection():
    from app.cyber import cve
    deb = 'ID=debian\nVERSION_ID="12"\n'
    assert cve._ecosystem(deb) == "Debian:12"
    ubu = 'ID=ubuntu\nVERSION_ID="22.04"\n'
    assert cve._ecosystem(ubu) == "Ubuntu:22.04"
    assert cve._ecosystem("ID=arch\n") is None


async def test_cve_scan_finds_vulns():
    from app.cyber import cve

    async def run(cmd, timeout=120):
        if "os-release" in cmd:
            return 'ID=debian\nVERSION_ID="12"\n'
        if "dpkg-query" in cmd:
            return "openssl 3.0.1\ncurl 7.88.0\n"
        return ""

    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"results": [{"vulns": [{"id": "CVE-2024-1"}]}, {}]}

    class _Client:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return _Resp()

    with patch("app.cyber.cve.httpx.AsyncClient", _Client):
        f = await cve.scan_packages(run)
    assert f and f[0]["check"] == "cve"
    assert "CVE potentielles" in f[0]["title"]


async def test_cve_no_packages():
    from app.cyber import cve
    async def run(cmd, timeout=120):
        return ""   # pas d'os-release -> écosystème None
    assert await cve.scan_packages(run) == []


# ─── Historique des scores ───────────────────────────────────────────────────

async def test_score_history_no_pool():
    from app.cyber import store
    with patch("app.cyber.store.get_pool", new=AsyncMock(return_value=None)):
        assert await store.score_history("h1") == []
        await store.save_score("h1", 80, "B")   # no-op, ne lève pas


def test_router_cyber_keywords():
    from app.registry import registry
    from app.router import route
    for p in ["audite la sécurité de unraid", "quelles failles", "durcis le pare-feu"]:
        assert route(p, registry).agent == "cyber", p
