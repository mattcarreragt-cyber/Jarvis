"""Connexion SSH aux hôtes de l'utilisateur (asyncssh).

Auth par clé : settings.cyber_ssh_key_path (ou agent SSH par défaut).
Connexions vers TES hôtes déclarés uniquement (usage défensif).

Best-effort : si asyncssh manque ou l'hôte est injoignable, on lève une
exception explicite que l'appelant transforme en message clair.
"""

from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger("jarvis.cyber.ssh")


def _client_keys() -> list[str] | None:
    return [settings.cyber_ssh_key_path] if settings.cyber_ssh_key_path else None


async def make_runner(host: dict):
    """Ouvre une connexion SSH. Retourne (conn, run) où run(cmd)->str (stdout+stderr)."""
    import asyncssh  # import paresseux

    conn = await asyncssh.connect(
        host["hostname"],
        port=host.get("port", 22),
        username=host["username"],
        client_keys=_client_keys(),
        known_hosts=None,            # homelab : on ne vérifie pas known_hosts
        connect_timeout=10,
    )

    async def run(cmd: str, timeout: int = 120) -> str:
        r = await conn.run(cmd, check=False, timeout=timeout)
        return ((r.stdout or "") + (r.stderr or "")).strip()

    return conn, run


async def run_once(host: dict, command: str, timeout: int = 120) -> dict:
    """Exécute UNE commande (utilisé pour la remédiation explicite). {ok, output|error}."""
    try:
        conn, run = await make_runner(host)
    except Exception as e:
        return {"ok": False, "error": f"Connexion SSH impossible : {e}"}
    try:
        out = await run(command, timeout=timeout)
        return {"ok": True, "output": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
