"""Agent Home Assistant.

Lecture : libre.
Écriture (turn_on/off) : nécessite confirmation (rule spec — ne pas casser l'existant).
"""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.agents.ha_tools import SPECS, get_entity, get_states, resolve_entities, set_temperature, turn_off, turn_on
from app.contracts import (
    AgentRequest,
    AgentResponse,
    AgentSpec,
    AgentStatus,
    ConfirmationRequest,
    ToolCall,
    ToolResult,
)

# Patterns d'action write détectés en langage naturel (inclut « on »/« off » seuls)
_ON_PAT   = re.compile(r"\b(allume\w*|active\w*|ouvre|démarre|demarre|lance|mets?\s+en\s+marche|turn\s*on|\bon\b)\b", re.I)
_OFF_PAT  = re.compile(r"\b(éteins?\w*|eteins?\w*|éteindre|eteindre|coupe\w*|ferme\w*|arrête\w*|arrete\w*|turn\s*off|\boff\b)\b", re.I)
# entity_id explicite (ex. light.salon) — chemin direct sans résolution
_ENT_PAT  = re.compile(r"\b(light|switch|sensor|climate|cover|media_player|input_boolean|fan)\.\w+", re.I)
# Consigne de température : « à 20 degrés », « 21° », « 20.5 °C », « régle à 19 »
_TEMP_PAT = re.compile(r"\b(\d{1,2}(?:[.,]\d)?)\s*(?:°\s*[cC]?|degr[eé]s?|degrés?)\b|\bà\s+(\d{1,2}(?:[.,]\d)?)\b", re.I)
# Mots qui déclenchent une consigne de température
_TEMP_VERBS = re.compile(r"\b(règle\w*|regle\w*|mets?\s+à|mettre\s+à|règle\w*|fixe\w*|consigne|chauffe\s+à|clim\s+à|température\s+à)\b", re.I)


class HomeAssistantAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="home_assistant",
            description="Contrôle et monitoring de la domotique Home Assistant : "
                        "lumières, capteurs, switches, chauffage, volets.",
            keywords=[
                "home assistant", "domotique", "lumière", "lumiere", "lampe",
                "chauffage", "volet", "climatisation", "capteur", "capteurs", "sensor",
                "switch", "allume", "éteins", "température", "humidité", "humidite",
                "co2", "qualité air", "présence", "presence", "alarme",
                "maison", "pièce", "salon", "chambre", "cuisine",
            ],
            tools=SPECS,
            default_permissions=["ha:read"],
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        msg = request.message

        # ── Détection consigne de température ────────────────────────────
        temp_match = _TEMP_PAT.search(msg)
        if temp_match and _TEMP_VERBS.search(msg):
            raw = (temp_match.group(1) or temp_match.group(2) or "").replace(",", ".")
            try:
                temperature = float(raw)
            except ValueError:
                temperature = None
            if temperature is not None and 5 <= temperature <= 35:
                entity_match = _ENT_PAT.search(msg)
                if entity_match:
                    entity_ids = [entity_match.group(0).lower()]
                    target = entity_ids[0]
                else:
                    entity_ids, target = await resolve_entities(msg)
                # Si aucune entité climate trouvée, propose le thermostat par défaut
                climate_ids = [e for e in entity_ids if e.startswith("climate.")]
                if not climate_ids and not entity_ids:
                    return AgentResponse(
                        request_id=request.request_id,
                        agent="home_assistant",
                        status=AgentStatus.ok,
                        content=(
                            f"Je n'ai pas trouvé à quel thermostat appliquer {temperature}°C. "
                            "Précise : « règle le chauffage à 20° » ou « règle la clim à 22° »."
                        ),
                    )
                target_ids = climate_ids or entity_ids
                shown = ", ".join(f"`{e}`" for e in target_ids)
                return AgentResponse(
                    request_id=request.request_id,
                    agent="home_assistant",
                    status=AgentStatus.needs_confirmation,
                    content=f"Je vais régler **{target}** à **{temperature}°C** → {shown}. Confirme ?",
                    confirmation=ConfirmationRequest(
                        request_id=request.request_id,
                        tool="ha.set_temperature",
                        args={"entity_id": target_ids[0] if len(target_ids) == 1 else target_ids, "temperature": temperature},
                        summary=f"Consigne {temperature}°C sur {target}",
                    ),
                )

        # ── Détection d'une action write ──────────────────────────────────
        is_off = bool(_OFF_PAT.search(msg))
        is_on  = bool(_ON_PAT.search(msg)) and not is_off   # « off » prime sur « on »
        entity_match = _ENT_PAT.search(msg)

        if is_on or is_off:
            action = "turn_on" if is_on else "turn_off"
            label  = "allumer" if is_on else "éteindre"

            # a) entity_id explicite fourni → chemin direct
            if entity_match:
                entity_ids = [entity_match.group(0).lower()]
                target = entity_ids[0]
            # b) sinon, on résout le nom parlé via alias + friendly_name
            else:
                entity_ids, target = await resolve_entities(msg)

            if not entity_ids:
                return AgentResponse(
                    request_id=request.request_id,
                    agent="home_assistant",
                    status=AgentStatus.ok,
                    content=(
                        "Je n'ai pas trouvé à quelle entité tu fais référence. "
                        "Tu peux :\n"
                        "- préciser le nom exact (ex. « allume light.salon »),\n"
                        "- ou déclarer un alias dans `config/ha_aliases.yaml` "
                        "(ex. `\"luminaires salon\": [light.salon_1, light.salon_2]`).\n\n"
                        "_Astuce : demande « liste les lumières » pour voir les noms réels._"
                    ),
                )

            shown = ", ".join(f"`{e}`" for e in entity_ids[:6])
            extra = f" (+{len(entity_ids) - 6})" if len(entity_ids) > 6 else ""
            return AgentResponse(
                request_id=request.request_id,
                agent="home_assistant",
                status=AgentStatus.needs_confirmation,
                content=f"Je vais **{label}** {target} → {shown}{extra}. Confirme ?",
                confirmation=ConfirmationRequest(
                    request_id=request.request_id,
                    tool=f"ha.{action}",
                    args={"entity_id": entity_ids if len(entity_ids) > 1 else entity_ids[0]},
                    summary=f"{label.capitalize()} {target}",
                ),
            )

        # ── Lecture : états ───────────────────────────────────────────────
        # Détection de domaine
        domain = None
        if any(w in msg.lower() for w in ["lumière", "lumiere", "lampe", "light"]):
            domain = "light"
        elif any(w in msg.lower() for w in ["switch", "prise"]):
            domain = "switch"
        elif any(w in msg.lower() for w in ["température", "capteur", "sensor", "humidité",
                                            "humidite", "co2", "présence", "presence", "qualité air"]):
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
