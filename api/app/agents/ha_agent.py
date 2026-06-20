"""Agent Home Assistant.

Lecture : libre.
Écriture (turn_on/off) : nécessite confirmation (rule spec — ne pas casser l'existant).
"""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.agents.ha_tools import SPECS, get_entity, get_states, turn_off, turn_on
from app.contracts import (
    AgentRequest,
    AgentResponse,
    AgentSpec,
    AgentStatus,
    ConfirmationRequest,
    ToolCall,
    ToolResult,
)

# Patterns d'action write détectés en langage naturel
_ON_PAT  = re.compile(r"\b(allume|active|ouvre|démarre|lance|turn.?on)\b",  re.I)
_OFF_PAT = re.compile(r"\b(éteins?|éteindre|coupe|ferme|arrête|turn.?off)\b", re.I)
_ENT_PAT = re.compile(r"\b(light|switch|sensor|climate|cover|media_player|input_boolean)\.\w+", re.I)


class HomeAssistantAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="home_assistant",
            description="Contrôle et monitoring de la domotique Home Assistant : "
                        "lumières, capteurs, switches, chauffage, volets.",
            keywords=[
                "home assistant", "domotique", "lumière", "lumiere", "lampe",
                "chauffage", "volet", "climatisation", "capteur", "sensor",
                "switch", "allume", "éteins", "température", "alarme",
                "maison", "pièce", "salon", "chambre", "cuisine",
            ],
            tools=SPECS,
            default_permissions=["ha:read"],
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        msg = request.message

        # ── Détection d'une action write ──────────────────────────────────
        is_on  = bool(_ON_PAT.search(msg))
        is_off = bool(_OFF_PAT.search(msg))
        entity_match = _ENT_PAT.search(msg)

        if (is_on or is_off) and entity_match:
            entity_id = entity_match.group(0).lower()
            action    = "turn_on" if is_on else "turn_off"
            label     = "allumer" if is_on else "éteindre"
            return AgentResponse(
                request_id=request.request_id,
                agent="home_assistant",
                status=AgentStatus.needs_confirmation,
                content=f"Je vais **{label}** `{entity_id}`. Confirme ?",
                confirmation=ConfirmationRequest(
                    request_id=request.request_id,
                    tool=f"ha.{action}",
                    args={"entity_id": entity_id},
                    summary=f"{label.capitalize()} {entity_id}",
                ),
            )

        # ── Lecture : états ───────────────────────────────────────────────
        # Détection de domaine
        domain = None
        if any(w in msg.lower() for w in ["lumière", "lumiere", "lampe", "light"]):
            domain = "light"
        elif any(w in msg.lower() for w in ["switch", "prise"]):
            domain = "switch"
        elif any(w in msg.lower() for w in ["température", "capteur", "sensor"]):
            domain = "sensor"
        elif any(w in msg.lower() for w in ["climatisation", "chauffage", "climate"]):
            domain = "climate"

        result = await get_states(domain=domain)
        calls  = [ToolCall(tool="ha.get_states", args={"domain": domain}, result=result)]
        return AgentResponse(
            request_id=request.request_id,
            agent="home_assistant",
            status=AgentStatus.ok,
            content=self._summarize(result, domain),
            tool_calls=calls,
        )

    @staticmethod
    def _summarize(result: ToolResult, domain: str | None) -> str:
        if not result.ok:
            return f"Impossible de joindre Home Assistant : {result.error}"

        states = result.data.get("states", [])
        total  = result.data.get("total", 0)
        label  = f"domaine `{domain}`" if domain else "toutes les entités"

        if not states:
            return f"Aucune entité trouvée ({label})."

        lines = [f"## Home Assistant — {label} ({total} entités)", ""]
        for s in states[:20]:
            name = s.get("friendly_name") or s["entity_id"]
            lines.append(f"- **{name}** : `{s['state']}`")
        if total > 20:
            lines.append(f"\n_…et {total - 20} autres entités._")
        return "\n".join(lines)
