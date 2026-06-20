"""Router d'agent — passe 1 à règles (voir docs/03_ROUTER.md).

Le fallback LLM (passe 2) sera branché à l'étape 7. Pour l'instant, si la
confiance des règles est insuffisante, on route vers l'agent par défaut.
"""

from __future__ import annotations

import re

from app.agents.base import AgentRegistry
from app.contracts import RouteDecision

HIGH_CONFIDENCE = 1.0   # au moins un keyword matché
MARGIN = 0.0            # marge minimale avec le 2e (souple au départ)
DEFAULT_AGENT = "echo"  # agent de conversation par défaut


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
