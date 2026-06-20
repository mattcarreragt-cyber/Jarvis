"""Outils Agent Dev — exécution de code dans un conteneur Docker sandbox.

Utilise le socket Docker monté en lecture+écriture (nécessaire pour run).
Tout code s'exécute dans un conteneur éphémère python:3.12-slim avec réseau désactivé.
Pas de GPU requis — tourne sur Unraid.
"""

from __future__ import annotations

import logging

from app.contracts import SideEffect, ToolResult, ToolSpec

logger = logging.getLogger("jarvis.dev")

_PY_IMAGE = "python:3.12-slim"
_BASH_IMAGE = "bash:5"
_TIMEOUT = 15  # secondes
_MAX_OUTPUT = 4096


async def _run_sandboxed(image: str, command: list[str], mem_limit: str) -> ToolResult:
    """Lance une commande en conteneur isolé (sans réseau) avec timeout strict.

    Détaché → wait(timeout) → kill si dépassement → logs → suppression.
    L'exécution Docker (bloquante) est déportée dans un thread.
    """
    try:
        import docker  # type: ignore
        from docker.errors import NotFound  # type: ignore
    except ImportError:
        return ToolResult(ok=False, error="SDK Docker non installé")

    import asyncio

    def _blocking() -> ToolResult:
        try:
            client = docker.from_env()
        except Exception as e:
            return ToolResult(ok=False, error=f"Docker indisponible : {e}"[:_MAX_OUTPUT])

        container = None
        try:
            container = client.containers.run(
                image,
                command,
                detach=True,
                network_mode="none",
                mem_limit=mem_limit,
                cpu_quota=50000,  # 50% d'un cœur
                stdout=True,
                stderr=True,
            )
            try:
                container.wait(timeout=_TIMEOUT)
            except Exception:
                # Timeout ou erreur d'attente → on tue le conteneur
                try:
                    container.kill()
                except Exception:
                    pass
                logs = container.logs().decode("utf-8", errors="replace")
                return ToolResult(
                    ok=False,
                    error=f"Délai dépassé ({_TIMEOUT}s). Sortie partielle :\n{logs}"[:_MAX_OUTPUT],
                )

            logs = container.logs().decode("utf-8", errors="replace")
            return ToolResult(ok=True, data={"output": logs[:_MAX_OUTPUT]})
        except Exception as e:
            return ToolResult(ok=False, error=str(e)[:_MAX_OUTPUT])
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except NotFound:
                    pass
                except Exception:
                    pass

    return await asyncio.to_thread(_blocking)


async def run_python(code: str) -> ToolResult:
    """Exécute du code Python dans un conteneur isolé sans réseau."""
    return await _run_sandboxed(_PY_IMAGE, ["python", "-c", code], "256m")


async def run_bash(script: str) -> ToolResult:
    """Exécute un script bash dans un conteneur isolé sans réseau."""
    return await _run_sandboxed(_BASH_IMAGE, ["bash", "-c", script], "128m")


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
