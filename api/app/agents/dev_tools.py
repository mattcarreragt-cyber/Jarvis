"""Outils Agent Dev — exécution de code dans un conteneur Docker sandbox.

Utilise le socket Docker monté en lecture+écriture (nécessaire pour run).
Tout code s'exécute dans un conteneur éphémère python:3.12-slim avec réseau désactivé.
Pas de GPU requis — tourne sur Unraid.
"""

from __future__ import annotations

import logging

from app.contracts import SideEffect, ToolResult, ToolSpec

logger = logging.getLogger("jarvis.dev")

_SANDBOX_IMAGE = "python:3.12-slim"
_TIMEOUT = 15  # secondes


async def run_python(code: str) -> ToolResult:
    """Exécute du code Python dans un conteneur isolé sans réseau."""
    try:
        import docker  # type: ignore
    except ImportError:
        return ToolResult(ok=False, error="SDK Docker non installé")

    try:
        client = docker.from_env()
        result = client.containers.run(
            _SANDBOX_IMAGE,
            ["python", "-c", code],
            remove=True,
            network_mode="none",
            mem_limit="256m",
            cpu_quota=50000,  # 50% d'un cœur
            timeout=_TIMEOUT,
            stdout=True,
            stderr=True,
        )
        output = result.decode("utf-8", errors="replace") if isinstance(result, bytes) else str(result)
        return ToolResult(ok=True, data={"output": output[:4096]})
    except Exception as e:
        return ToolResult(ok=False, error=str(e)[:512])


async def run_bash(script: str) -> ToolResult:
    """Exécute un script bash dans un conteneur isolé sans réseau."""
    try:
        import docker  # type: ignore
    except ImportError:
        return ToolResult(ok=False, error="SDK Docker non installé")

    try:
        client = docker.from_env()
        result = client.containers.run(
            "bash:5",
            ["bash", "-c", script],
            remove=True,
            network_mode="none",
            mem_limit="128m",
            cpu_quota=50000,
            timeout=_TIMEOUT,
            stdout=True,
            stderr=True,
        )
        output = result.decode("utf-8", errors="replace") if isinstance(result, bytes) else str(result)
        return ToolResult(ok=True, data={"output": output[:4096]})
    except Exception as e:
        return ToolResult(ok=False, error=str(e)[:512])


HANDLERS = {
    "dev.run_python": run_python,
    "dev.run_bash":   run_bash,
}

SPECS = [
    ToolSpec(
        name="dev.run_python",
        description="Exécute du code Python en sandbox Docker (sans réseau, sans GPU)",
        parameters={"code": {"type": "string"}},
        required_permissions=["dev:execute"],
        side_effects=SideEffect.none,
    ),
    ToolSpec(
        name="dev.run_bash",
        description="Exécute un script bash en sandbox Docker (sans réseau, sans GPU)",
        parameters={"script": {"type": "string"}},
        required_permissions=["dev:execute"],
        side_effects=SideEffect.none,
    ),
]
