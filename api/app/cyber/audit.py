"""Batterie d'analyses de sécurité read-only via SSH.

Chaque check exécute une commande de lecture et produit des findings avec
sévérité + recommandation + (optionnel) commande de remédiation proposée.
Tout est NON destructif. La remédiation n'est jamais appliquée ici.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field

from app.cyber import cve, nmap_scan, ssh

logger = logging.getLogger("jarvis.cyber.audit")

SEVERITIES = ["critical", "high", "medium", "low", "info"]
# Pénalité de score par sévérité (base 100)
_WEIGHTS = {"critical": 30, "high": 15, "medium": 6, "low": 2, "info": 0}


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


async def _check_lynis(run) -> list[Finding]:
    """Lance lynis sur l'hôte (audit système complet) si disponible."""
    out = await run(
        "command -v lynis >/dev/null 2>&1 && "
        "sudo lynis audit system --quiet --no-colors 2>/dev/null | "
        "grep -iE 'hardening index|warning|suggestion' | head -n 40 "
        "|| echo __NOLYNIS__", timeout=900)
    if "__NOLYNIS__" in out or not out.strip():
        return [Finding("lynis", "info", "Lynis non installé (audit système approfondi indisponible)",
                        "", "Installer lynis pour un audit système complet.",
                        "sudo apt-get install -y lynis")]
    f = []
    m = re.search(r"hardening index[^\d]*(\d{1,3})", out, re.I)
    if m:
        idx = int(m.group(1))
        sev = "high" if idx < 50 else "medium" if idx < 70 else "low" if idx < 85 else "info"
        f.append(Finding("lynis", sev, f"Indice de durcissement Lynis : {idx}/100",
                         "", "Suivre les suggestions Lynis pour augmenter l'indice."))
    warns = [l.strip() for l in out.splitlines() if re.search(r"warning", l, re.I)][:8]
    if warns:
        f.append(Finding("lynis", "medium", f"{len(warns)} avertissement(s) Lynis",
                         "\n".join(warns), "Traiter les avertissements remontés par Lynis."))
    return f


async def _check_rootkits(run) -> list[Finding]:
    """Détection de rootkits via rkhunter, sinon chkrootkit."""
    out = await run(
        "if command -v rkhunter >/dev/null 2>&1; then "
        "  sudo rkhunter --check --sk --nocolors 2>/dev/null | grep -iE 'warning|infected'; "
        "elif command -v chkrootkit >/dev/null 2>&1; then "
        "  sudo chkrootkit 2>/dev/null | grep -iE 'INFECTED'; "
        "else echo __NORK__; fi", timeout=600)
    if "__NORK__" in out or not out.strip():
        if "__NORK__" in out:
            return [Finding("rootkit", "info", "Aucun scanner de rootkit installé",
                            "", "Installer rkhunter ou chkrootkit pour détecter les rootkits.",
                            "sudo apt-get install -y rkhunter")]
        return []  # scanner présent, rien remonté
    infected = [l.strip() for l in out.splitlines() if re.search(r"infected", l, re.I)]
    warns = [l.strip() for l in out.splitlines() if re.search(r"warning", l, re.I)]
    f = []
    if infected:
        f.append(Finding("rootkit", "critical", f"{len(infected)} indicateur(s) d'infection détecté(s)",
                         "\n".join(infected[:10]),
                         "Investiguer immédiatement : possible compromission."))
    if warns:
        f.append(Finding("rootkit", "medium", f"{len(warns)} avertissement(s) rkhunter",
                         "\n".join(warns[:10]), "Vérifier chaque avertissement rkhunter."))
    return f


async def _check_cve(run) -> list[Finding]:
    """Corrélation CVE des paquets installés (OSV.dev)."""
    dicts = await cve.scan_packages(run)
    return [Finding(**d) for d in dicts]


_CHECKS = [
    _check_root_users, _check_empty_passwords, _check_sshd, _check_firewall,
    _check_updates, _check_ports, _check_docker, _check_failed_logins,
    _check_rootkits, _check_lynis, _check_cve, _check_suid,
]


def compute_score(findings: list[dict]) -> tuple[int, str]:
    """Score 0-100 + grade A-F à partir des findings (par sévérité)."""
    penalty = sum(_WEIGHTS.get(f.get("severity", "info"), 0) for f in findings)
    score = max(0, 100 - penalty)
    grade = ("A" if score >= 90 else "B" if score >= 75 else
             "C" if score >= 60 else "D" if score >= 40 else "F")
    return score, grade


async def run_checks(run) -> list[Finding]:
    findings: list[Finding] = []
    for check in _CHECKS:
        try:
            findings += await check(run)
        except Exception as e:
            logger.debug("check %s: %s", getattr(check, "__name__", "?"), e)
    return findings


def _summary(findings: list[dict]) -> dict:
    s = {sev: 0 for sev in SEVERITIES}
    for f in findings:
        s[f["severity"]] = s.get(f["severity"], 0) + 1
    return s


async def run_audit(host: dict, runner=None, with_nmap: bool = True) -> dict:
    """Audit complet d'un hôte (SSH + nmap + lynis + scoring). runner injectable."""
    close = None
    if runner is None:
        try:
            conn, runner = await ssh.make_runner(host)
            close = conn.close
        except Exception as e:
            return {"ok": False, "error": f"Connexion SSH impossible : {e}"}
    try:
        findings = [asdict(f) for f in await run_checks(runner)]
    finally:
        if close:
            close()

    # Scan réseau nmap (depuis le conteneur, n'utilise pas SSH)
    if with_nmap and host.get("hostname"):
        try:
            findings += await nmap_scan.scan(host["hostname"])
        except Exception as e:
            logger.debug("nmap: %s", e)

    score, grade = compute_score(findings)
    return {"ok": True, "findings": findings, "summary": _summary(findings),
            "score": score, "grade": grade}
