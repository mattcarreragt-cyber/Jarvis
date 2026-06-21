"""Batterie d'analyses de sécurité read-only via SSH.

Chaque check exécute une commande de lecture et produit des findings avec
sévérité + recommandation + (optionnel) commande de remédiation proposée.
Tout est NON destructif. La remédiation n'est jamais appliquée ici.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field

from app.cyber import ssh

logger = logging.getLogger("jarvis.cyber.audit")

SEVERITIES = ["critical", "high", "medium", "low", "info"]


@dataclass
class Finding:
    check: str
    severity: str
    title: str
    detail: str = ""
    recommendation: str = ""
    remediation: str = ""


# ── Checks individuels ───────────────────────────────────────────────────────
# Chaque check : async (run) -> list[Finding]. `run(cmd)` renvoie stdout+stderr.

async def _check_sshd(run) -> list[Finding]:
    out = await run("sshd -T 2>/dev/null || cat /etc/ssh/sshd_config 2>/dev/null")
    f = []
    low = out.lower()
    if re.search(r"permitrootlogin\s+yes", low):
        f.append(Finding("sshd", "high", "Connexion SSH root autorisée",
                         "PermitRootLogin yes", "Désactiver le login root direct.",
                         "sudo sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && sudo systemctl restart ssh"))
    if re.search(r"passwordauthentication\s+yes", low):
        f.append(Finding("sshd", "medium", "Authentification SSH par mot de passe activée",
                         "PasswordAuthentication yes", "Préférer l'auth par clé et désactiver les mots de passe.",
                         "sudo sed -i 's/^#\\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && sudo systemctl restart ssh"))
    return f


async def _check_updates(run) -> list[Finding]:
    out = await run("apt-get -s -o Debug::NoLocking=true upgrade 2>/dev/null | grep -c '^Inst' || echo 0")
    m = re.search(r"\d+", out)
    n = int(m.group()) if m else 0
    if n > 0:
        sev = "high" if n > 30 else "medium" if n > 0 else "info"
        return [Finding("updates", sev, f"{n} mise(s) à jour en attente",
                        f"{n} paquets à mettre à jour.", "Appliquer les mises à jour de sécurité.",
                        "sudo apt-get update && sudo apt-get -y upgrade")]
    return []


async def _check_ports(run) -> list[Finding]:
    out = await run("ss -tlnH 2>/dev/null || netstat -tlnp 2>/dev/null")
    exposed = []
    for line in out.splitlines():
        if "0.0.0.0:" in line or "*:" in line or ":::" in line:
            m = re.search(r"[0.:*]+:(\d+)", line)
            if m:
                exposed.append(m.group(1))
    exposed = sorted(set(exposed))
    if exposed:
        return [Finding("ports", "info", f"{len(exposed)} port(s) en écoute sur toutes les interfaces",
                        "Ports: " + ", ".join(exposed),
                        "Vérifier que chaque port exposé est nécessaire ; restreindre via pare-feu.")]
    return []


async def _check_firewall(run) -> list[Finding]:
    out = (await run("sudo ufw status 2>/dev/null; sudo iptables -S 2>/dev/null")).lower()
    if "status: active" in out or re.search(r"-p\s", out):
        return []
    return [Finding("firewall", "medium", "Aucun pare-feu actif détecté",
                    "ufw inactif et aucune règle iptables.", "Activer un pare-feu.",
                    "sudo ufw default deny incoming && sudo ufw allow OpenSSH && sudo ufw --force enable")]


async def _check_root_users(run) -> list[Finding]:
    out = await run("awk -F: '($3==0){print $1}' /etc/passwd 2>/dev/null")
    extras = [u for u in out.split() if u and u != "root"]
    if extras:
        return [Finding("users", "critical", "Compte(s) supplémentaire(s) avec UID 0",
                        "UID 0 : " + ", ".join(extras),
                        "Un seul compte (root) doit avoir l'UID 0. Investiguer immédiatement.")]
    return []


async def _check_empty_passwords(run) -> list[Finding]:
    out = await run("sudo awk -F: '($2==\"\"){print $1}' /etc/shadow 2>/dev/null")
    empties = [u for u in out.split() if u]
    if empties:
        return [Finding("passwords", "critical", "Compte(s) sans mot de passe",
                        ", ".join(empties), "Définir un mot de passe ou verrouiller ces comptes.",
                        "sudo passwd -l " + (empties[0] if empties else "USER"))]
    return []


async def _check_docker(run) -> list[Finding]:
    out = await run("docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null")
    if not out:
        return []
    f = []
    for line in out.splitlines():
        if "0.0.0.0:" in line:
            name = line.split()[0]
            f.append(Finding("docker", "low", f"Conteneur exposé : {name}",
                             line, "Vérifier que l'exposition publique du port est voulue."))
    priv = await run("docker ps -q 2>/dev/null | xargs -r docker inspect --format '{{.Name}} {{.HostConfig.Privileged}}' 2>/dev/null | grep -i true")
    for line in priv.splitlines():
        if line.strip():
            f.append(Finding("docker", "high", f"Conteneur privilégié : {line.split()[0]}",
                             line, "Éviter --privileged ; restreindre les capabilities."))
    return f


async def _check_suid(run) -> list[Finding]:
    # Peut être lent (parcours du FS) — acceptable pour un audit poussé.
    out = await run("find / -perm -4000 -type f 2>/dev/null | head -n 200", timeout=300)
    binaries = [b for b in out.splitlines() if b.strip()]
    risky = [b for b in binaries if re.search(r"/(nmap|vim|find|bash|more|less|nano|cp|python)", b)]
    if risky:
        return [Finding("suid", "medium", f"{len(risky)} binaire(s) SUID potentiellement risqué(s)",
                        ", ".join(risky[:10]), "Retirer le bit SUID des binaires non nécessaires.")]
    return [Finding("suid", "info", f"{len(binaries)} binaires SUID recensés",
                    "Revue manuelle conseillée.")] if binaries else []


async def _check_failed_logins(run) -> list[Finding]:
    out = await run("sudo grep -c 'Failed password' /var/log/auth.log 2>/dev/null || echo 0")
    m = re.search(r"\d+", out)
    n = int(m.group()) if m else 0
    if n > 50:
        return [Finding("auth", "medium", f"{n} tentatives de connexion échouées",
                        "Possible attaque par force brute.",
                        "Installer fail2ban et restreindre l'accès SSH.",
                        "sudo apt-get install -y fail2ban && sudo systemctl enable --now fail2ban")]
    return []


_CHECKS = [
    _check_root_users, _check_empty_passwords, _check_sshd, _check_firewall,
    _check_updates, _check_ports, _check_docker, _check_failed_logins, _check_suid,
]


async def run_checks(run) -> list[Finding]:
    findings: list[Finding] = []
    for check in _CHECKS:
        try:
            findings += await check(run)
        except Exception as e:
            logger.debug("check %s: %s", getattr(check, "__name__", "?"), e)
    return findings


def _summary(findings: list[Finding]) -> dict:
    s = {sev: 0 for sev in SEVERITIES}
    for f in findings:
        s[f.severity] = s.get(f.severity, 0) + 1
    return s


async def run_audit(host: dict, runner=None) -> dict:
    """Audit complet d'un hôte. runner injectable pour les tests."""
    close = None
    if runner is None:
        try:
            conn, runner = await ssh.make_runner(host)
            close = conn.close
        except Exception as e:
            return {"ok": False, "error": f"Connexion SSH impossible : {e}"}
    try:
        findings = await run_checks(runner)
        return {"ok": True,
                "findings": [asdict(f) for f in findings],
                "summary": _summary(findings)}
    finally:
        if close:
            close()
