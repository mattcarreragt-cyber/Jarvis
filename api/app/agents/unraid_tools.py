"""Outils de l'agent Unraid — lecture via Docker socket + fichiers d'état Unraid.

Tous en lecture seule (v1). Les actions write (restart, start, stop) seront
ajoutées en v2 avec needs_confirmation obligatoire.

Montages requis dans docker-compose (voir commentaires) :
  - /var/run/docker.sock (Docker socket)
  - /var/local/emhttp (état Unraid, read-only)
"""

from __future__ import annotations

import configparser
import logging
import os
from pathlib import Path

from app.contracts import SideEffect, ToolResult, ToolSpec

logger = logging.getLogger("jarvis.unraid")

# Chemins montés depuis l'hôte Unraid
EMHTTP = Path(os.getenv("UNRAID_EMHTTP_PATH", "/var/local/emhttp"))
DOCKER_SOCKET = os.getenv("DOCKER_SOCKET", "/var/run/docker.sock")


def _docker_client():
    """Retourne un client Docker ou None si le socket est absent."""
    try:
        import docker
        return docker.DockerClient(base_url=f"unix://{DOCKER_SOCKET}", timeout=5)
    except Exception as e:
        logger.warning("Docker socket indisponible: %s", e)
        return None


def containers() -> ToolResult:
    """Liste des conteneurs Docker (nom, image, état, ports)."""
    client = _docker_client()
    if client is None:
        return ToolResult(ok=False, error="Docker socket non accessible")
    try:
        items = []
        for c in client.containers.list(all=True):
            ports = list(c.ports.keys()) if c.ports else []
            items.append({
                "id":     c.short_id,
                "name":   c.name,
                "image":  c.image.tags[0] if c.image.tags else c.image.short_id,
                "status": c.status,
                "ports":  ports[:4],   # limite pour lisibilité
            })
        items.sort(key=lambda x: (x["status"] != "running", x["name"]))
        return ToolResult(ok=True, data={"containers": items, "total": len(items)})
    except Exception as e:
        return ToolResult(ok=False, error=str(e))
    finally:
        client.close()


def array_status() -> ToolResult:
    """État de l'array Unraid (via /var/local/emhttp/var.ini)."""
    ini = EMHTTP / "var.ini"
    if not ini.exists():
        return ToolResult(
            ok=False,
            error=f"Fichier {ini} absent — monte /var/local/emhttp dans le conteneur",
        )
    try:
        cfg = configparser.ConfigParser(strict=False)
        # var.ini n'a pas de section header, on en ajoute un fictif
        content = "[root]\n" + ini.read_text(errors="replace")
        cfg.read_string(content)
        s = cfg["root"]
        return ToolResult(ok=True, data={
            "md_state":    s.get("mdState",    "unknown").strip('"'),
            "md_num_disks": s.get("mdNumDisks", "?").strip('"'),
            "version":     s.get("version",    "?").strip('"'),
        })
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def disks_status() -> ToolResult:
    """État des disques de l'array (via /var/local/emhttp/disks.ini)."""
    ini = EMHTTP / "disks.ini"
    if not ini.exists():
        return ToolResult(
            ok=False,
            error=f"Fichier {ini} absent — monte /var/local/emhttp dans le conteneur",
        )
    try:
        cfg = configparser.ConfigParser(strict=False)
        cfg.read_string(ini.read_text(errors="replace"))
        disks = []
        for section in cfg.sections():
            s = cfg[section]
            disks.append({
                "name":   section,
                "device": s.get("device",  "?").strip('"'),
                "status": s.get("status",  "?").strip('"'),
                "temp":   s.get("temp",    "?").strip('"'),
                "fsSize": s.get("fsSize",  "?").strip('"'),
                "fsFree": s.get("fsFree",  "?").strip('"'),
            })
        return ToolResult(ok=True, data={"disks": disks})
    except Exception as e:
        return ToolResult(ok=False, error=str(e))


def docker_stats() -> ToolResult:
    """Résumé : running / stopped / total."""
    client = _docker_client()
    if client is None:
        return ToolResult(ok=False, error="Docker socket non accessible")
    try:
        all_c = client.containers.list(all=True)
        running = sum(1 for c in all_c if c.status == "running")
        return ToolResult(ok=True, data={
            "running": running,
            "stopped": len(all_c) - running,
            "total":   len(all_c),
        })
    except Exception as e:
        return ToolResult(ok=False, error=str(e))
    finally:
        client.close()


HANDLERS = {
    "unraid.containers":   containers,
    "unraid.array_status": array_status,
    "unraid.disks_status": disks_status,
    "unraid.docker_stats": docker_stats,
}

SPECS = [
    ToolSpec(name="unraid.containers",   description="Liste tous les conteneurs Docker (nom, image, état)",
             required_permissions=["unraid:read"], side_effects=SideEffect.read),
    ToolSpec(name="unraid.array_status", description="État de l'array Unraid (démarré, arrêté, parité)",
             required_permissions=["unraid:read"], side_effects=SideEffect.read),
    ToolSpec(name="unraid.disks_status", description="État des disques de l'array (santé, température, espace)",
             required_permissions=["unraid:read"], side_effects=SideEffect.read),
    ToolSpec(name="unraid.docker_stats", description="Résumé conteneurs : combien en cours, stoppés, total",
             required_permissions=["unraid:read"], side_effects=SideEffect.none),
]
