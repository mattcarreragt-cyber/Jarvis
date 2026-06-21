"""Exécuteur d'agenda — boucle de fond qui déclenche les tâches dues.

- kind=reminder : crée une notification avec le texte du rappel.
- kind=prompt   : route le message vers l'agent adéquat et notifie le résultat.

Lancé au démarrage via le lifespan FastAPI. Tolérant aux pannes.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.automation import store

logger = logging.getLogger("jarvis.agenda.runner")

CHECK_INTERVAL = 30   # secondes


async def _execute(task: dict) -> None:
    label = task["label"]
    if task["kind"] == "reminder":
        await store.add_notification(f"⏰ {task['payload']}", source=label)
    else:  # prompt
        text = await _run_prompt(task["payload"])
        await store.add_notification(text, source=label)
    await store.mark_ran(task["id"], task["schedule_kind"],
                         task.get("time_of_day"), task.get("interval_sec"))


async def _run_prompt(message: str) -> str:
    """Route un message via le pipeline d'agents et renvoie la réponse (texte)."""
    try:
        from app.contracts import AgentRequest
        from app.registry import registry
        from app.router import route
        decision = route(message, registry)
        agent = registry.get(decision.agent) or registry.get("echo")
        resp = await agent.handle(AgentRequest(
            request_id=str(uuid.uuid4()), session_id="agenda",
            intent=decision.agent, message=message,
        ))
        return f"📋 {message}\n\n{resp.content}"
    except Exception as e:
        logger.warning("run_prompt: %s", e)
        return f"📋 {message}\n\n_(échec de l'exécution : {e})_"


async def tick() -> int:
    """Exécute toutes les tâches dues. Retourne le nombre exécuté."""
    due = await store.due_tasks()
    for task in due:
        try:
            await _execute(task)
        except Exception as e:
            logger.warning("execute task %s: %s", task.get("id"), e)
    return len(due)


async def loop() -> None:
    logger.info("Agenda : boucle d'exécution démarrée (tick %ds)", CHECK_INTERVAL)
    await asyncio.sleep(5)
    while True:
        try:
            await tick()
        except Exception as e:
            logger.error("agenda loop: %s", e)
        await asyncio.sleep(CHECK_INTERVAL)
