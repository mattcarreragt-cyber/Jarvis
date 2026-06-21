"""Router d'agent — passe 1 à règles + passe 2 LLM (voir docs/03_ROUTER.md).

- Passe 1 (`route`) : scoring par mots-clés, synchrone, sans dépendance.
- Passe 2 (`route_smart`) : si la passe 1 n'est pas confiante (aucun mot-clé),
  on demande au LLM (chat.fast) de classer l'intention. Best-effort : si le LLM
  est injoignable (Kubuntu éteint), on conserve le repli de la passe 1 (chat).
"""

from __future__ import annotations

import logging
import re

from app.agents.base import AgentRegistry
from app.contracts import RouteDecision

logger = logging.getLogger("jarvis.router")

HIGH_CONFIDENCE = 1.0   # au moins un keyword matché
MARGIN = 0.0            # marge minimale avec le 2e (souple au départ)
DEFAULT_AGENT = "chat"  # agent de conversation généraliste par défaut


def _score(message: str, keywords: list[str]) -> float:
    """Nombre de keywords présents dans le message (insensible à la casse)."""
    text = message.lower()
    return sum(
        1.0
        for kw in keywords
        if re.search(rf"\b{re.escape(kw.lower())}\b", text)
    )


def route(message: str, registry: AgentRegistry, force_agent: str | None = None) -> RouteDecision:
    # Bypass explicite
    if force_agent:
        return RouteDecision(agent=force_agent, method="forced")

    # Passe 1 — scoring par keywords
    scored = [
        (spec.name, _score(message, spec.keywords))
        for spec in registry.specs()
        if spec.keywords  # l'agent par défaut (sans keywords) ne concourt pas
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    best = scored[0] if scored else (DEFAULT_AGENT, 0.0)
    second_score = scored[1][1] if len(scored) > 1 else 0.0

    if best[1] >= HIGH_CONFIDENCE and (best[1] - second_score) >= MARGIN:
        return RouteDecision(agent=best[0], method="rules", score=best[1])

    # Passe 2 (LLM) non encore branchée → fallback agent par défaut
    return RouteDecision(agent=DEFAULT_AGENT, method="rules", score=0.0)


# Agents exclus de la classification LLM (fallback / méta)
_NON_ROUTABLE = {"echo", "chat"}


async def classify_llm(message: str, registry: AgentRegistry) -> str | None:
    """Demande au LLM de choisir l'agent le plus adapté. None si indisponible."""
    specs = [s for s in registry.specs() if s.name not in _NON_ROUTABLE]
    if not specs:
        return None
    listing = "\n".join(f"- {s.name} : {s.description}" for s in specs)
    system = (
        "Tu es un routeur d'intention pour un assistant. À partir du message de "
        "l'utilisateur, choisis l'agent le plus adapté dans la liste. Réponds "
        "UNIQUEMENT par le nom exact de l'agent, ou par 'chat' si aucun ne convient. "
        "Aucune explication."
    )
    user = f"Agents disponibles :\n{listing}\n\nMessage : {message}\n\nAgent :"
    try:
        from app.llm.ollama import chat
        resp = await chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.0,
        )
    except Exception as e:
        logger.debug("classify_llm: %s", e)
        return None
    if not resp:
        return None
    low = resp.strip().lower()
    # Match le nom d'agent présent dans la réponse (le plus long d'abord)
    for name in sorted((s.name for s in specs), key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", low):
            return name
    return None


async def route_smart(message: str, registry: AgentRegistry,
                      force_agent: str | None = None) -> RouteDecision:
    """Passe 1 (règles) puis, si non confiant, passe 2 (LLM)."""
    decision = route(message, registry, force_agent)
    # Confiant (forcé ou keyword matché) → on garde
    if force_agent or (decision.score and decision.score >= HIGH_CONFIDENCE):
        return decision
    # Ambigu / aucun mot-clé → classification LLM (best-effort)
    name = await classify_llm(message, registry)
    if name and registry.get(name):
        logger.info("route LLM: '%s' → %s", message[:40], name)
        return RouteDecision(agent=name, method="llm", score=None)
    return decision
