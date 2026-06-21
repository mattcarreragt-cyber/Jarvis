"""Scan réseau nmap (depuis le conteneur API vers l'hôte cible).

Détecte les ports ouverts et services exposés, signale les services à risque.
Nécessite nmap installé dans le conteneur API (voir api/Dockerfile).
Best-effort : nmap absent ou hôte injoignable → liste vide.
"""

from __future__ import annotations

import asyncio
import logging
import re

logger = logging.getLogger("jarvis.cyber.nmap")

# port -> (service lisible, sévérité si exposé)
_RISKY = {
    "21": ("FTP", "high"), "23": ("Telnet", "critical"), "139": ("NetBIOS", "high"),
    "445": ("SMB", "high"), "3389": ("RDP", "high"), "5900": ("VNC", "high"),
    "3306": ("MySQL", "medium"), "5432": ("PostgreSQL", "medium"),
    "6379": ("Redis", "high"), "27017": ("MongoDB", "high"),
    "9200": ("Elasticsearch", "high"), "11211": ("Memcached", "high"),
    "2375": ("Docker API", "critical"), "25": ("SMTP", "low"),
}


def _parse_grepable(text: str) -> list[dict]:
    """Parse la sortie nmap -oG et produit des findings."""
    findings: list[dict] = []
    ports: list[tuple[str, str]] = []   # (port, service)
    for line in text.splitlines():
        if "Ports:" not in line:
            continue
        block = line.split("Ports:", 1)[1]
        for entry in block.split(","):
            m = re.match(r"\s*(\d+)/open/tcp//([^/]*)", entry)
            if m:
                ports.append((m.group(1), m.group(2) or "?"))

    if ports:
        listing = ", ".join(f"{p}/{s}" for p, s in ports)
        findings.append({
            "check": "nmap", "severity": "info",
            "title": f"{len(ports)} port(s) ouvert(s) (scan réseau)",
            "detail": listing, "recommendation": "Fermer/filtrer les ports non nécessaires.",
            "remediation": "",
        })
    for port, svc in ports:
        if port in _RISKY:
            name, sev = _RISKY[port]
            findings.append({
                "check": "nmap", "severity": sev,
                "title": f"Service sensible exposé : {name} (port {port})",
                "detail": f"{port}/tcp ouvert ({svc})",
                "recommendation": f"Restreindre {name} au réseau interne ou via VPN/pare-feu.",
                "remediation": "",
            })
    return findings


async def scan(hostname: str, top_ports: int = 1000) -> list[dict]:
    if not hostname:
        return []
    cmd = ["nmap", "-Pn", "-sT", "-sV", "-T4", f"--top-ports", str(top_ports), "-oG", "-", hostname]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except FileNotFoundError:
        logger.debug("nmap non installé dans le conteneur")
        return []
    except Exception as e:
        logger.debug("nmap lancement: %s", e)
        return []
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=600)
        return _parse_grepable(out.decode("utf-8", errors="replace"))
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        logger.warning("nmap: délai dépassé pour %s", hostname)
        return []
    except Exception as e:
        logger.debug("nmap: %s", e)
        return []
