"""Corrélation CVE — relève les paquets installés et interroge OSV.dev.

Collecte (Debian/Ubuntu) `dpkg-query`, déduit l'écosystème depuis /etc/os-release,
puis interroge l'API OSV (querybatch) pour trouver les vulnérabilités connues.

Best-effort : pas de réseau, OS non géré ou aucun paquet → liste vide.
"""

from __future__ import annotations

import logging
import re

import httpx

logger = logging.getLogger("jarvis.cyber.cve")

_OSV_BATCH = "https://api.osv.dev/v1/querybatch"
_MAX_PKGS = 400


def _ecosystem(os_release: str) -> str | None:
    """Déduit l'écosystème OSV depuis /etc/os-release (ex. 'Debian:12')."""
    fields = dict(re.findall(r'^(\w+)=["\']?([^"\'\n]+)', os_release, re.M))
    oid = (fields.get("ID") or "").lower()
    ver = fields.get("VERSION_ID", "")
    if oid == "debian" and ver:
        return f"Debian:{ver}"
    if oid == "ubuntu" and ver:
        return f"Ubuntu:{ver}"
    return None


def _parse_packages(dump: str) -> list[tuple[str, str]]:
    pkgs = []
    for line in dump.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            pkgs.append((parts[0], parts[1]))
    return pkgs[:_MAX_PKGS]


async def scan_packages(run) -> list[dict]:
    """run : async (cmd)->str (SSH). Retourne des findings CVE."""
    eco = _ecosystem(await run("cat /etc/os-release 2>/dev/null"))
    if not eco:
        return []
    pkgs = _parse_packages(
        await run("dpkg-query -W -f='${Package} ${Version}\\n' 2>/dev/null"))
    if not pkgs:
        return []

    queries = [{"package": {"ecosystem": eco, "name": n}, "version": v} for n, v in pkgs]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(_OSV_BATCH, json={"queries": queries})
            r.raise_for_status()
            results = r.json().get("results", [])
    except Exception as e:
        logger.debug("OSV indisponible: %s", e)
        return []

    vuln_pkgs: list[tuple[str, list[str]]] = []
    for (name, _ver), res in zip(pkgs, results):
        vulns = (res or {}).get("vulns") or []
        if vulns:
            vuln_pkgs.append((name, [v.get("id", "?") for v in vulns]))

    if not vuln_pkgs:
        return [{"check": "cve", "severity": "info",
                 "title": f"Aucune CVE connue ({len(pkgs)} paquets analysés)",
                 "detail": f"Écosystème {eco}.", "recommendation": "", "remediation": ""}]

    total = sum(len(ids) for _, ids in vuln_pkgs)
    detail = "; ".join(f"{n}: {', '.join(ids[:3])}" for n, ids in vuln_pkgs[:20])
    sev = "critical" if total > 40 else "high"
    return [{"check": "cve", "severity": sev,
             "title": f"{total} CVE potentielles sur {len(vuln_pkgs)} paquet(s)",
             "detail": detail,
             "recommendation": "Mettre à jour les paquets concernés ; vérifier les CVE sur osv.dev.",
             "remediation": "sudo apt-get update && sudo apt-get -y upgrade"}]
