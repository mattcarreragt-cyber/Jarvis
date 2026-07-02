"""Agent Home Assistant — exécution directe, sans demande de confirmation.

Garde-fous : les questions (« le four est-il éteint ? ») restent en lecture ;
seuls les impératifs (« éteins », « allume », « règle à 21° ») déclenchent
une action. Les participes (« allumée », « éteinte ») et le pronom « on »
ne comptent pas comme des ordres.
"""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.agents.ha_tools import (
    CONTROLLABLE_DOMAINS,
    SPECS,
    get_entity,
    get_states,
    resolve_entities,
    set_temperature,
    turn_off,
    turn_on,
)
from app.contracts import (
    AgentRequest,
    AgentResponse,
    AgentSpec,
    AgentStatus,
    ToolCall,
    ToolResult,
)

# Question / interrogation → toujours en lecture, jamais une action.
_QUESTION_PAT = re.compile(
    r"\?"
    r"|^\s*(est[- ]ce|quel(le)?s?|qui|combien|pourquoi|comment|quand|o[uù])\b"
    r"|\b(est[- ](il|elle|ce)|sont[- ](ils|elles))\b",
    re.I)

# Impératifs uniquement — les formes conjuguées participe (« allumée »,
# « éteinte ») ne matchent pas. « on »/« off » seuls : en fin de message
# uniquement (ex. « Luminaires salon ON »).
_ON_PAT = re.compile(
    r"\b(allume[sz]?|active[sz]?|activer|ouvre[sz]?|ouvrir"
    r"|démarre[sz]?|demarre[sz]?|lance[sz]?|mets?\s+en\s+marche|turn\s+on)\b"
    r"|\bon\s*[.!]?\s*$",
    re.I)
_OFF_PAT = re.compile(
    r"\b(éteins|éteignez|éteindre|eteins|eteignez|eteindre"
    r"|coupe[sz]?|couper|ferme[sz]?|fermer|arrête[sz]?|arrete[sz]?"
    r"|arrêter|arreter|stop|turn\s+off)\b"
    r"|\boff\s*[.!]?\s*$",
    re.I)

# entity_id explicite (ex. light.salon) — chemin direct sans résolution.
_ENT_PAT = re.compile(
    r"\b(" + "|".join(CONTROLLABLE_DOMAINS + ["sensor"]) + r")\.\w+", re.I)

# Consigne de température : « 21°C », « 20 degrés », « à 21 » (mais pas
# « à 15 h/heures » ni « à 50% » — expressions horaires/pourcentages exclues).
_TEMP_PAT = re.compile(
    r"\b(\d{1,2}(?:[.,]\d)?)\s*(?:°\s*c?|degr[eé]s?)(?!\w)"
    r"|\bà\s+(\d{1,2}(?:[.,]\d)?)(?!\s*(?:h\b|heures?\b|%|min\b))(?!\w)",
    re.I)
_TEMP_VERBS = re.compile(
    r"\b(règle\w*|regle\w*|mets?\b|mettre|fixe\w*|consigne"
    r"|monte\w*|baisse\w*|chauffe\w*|température|temperature)\b",
    re.I)


async def _resolve_target(msg: str) -> tuple[list[str], str]:
    """entity_id explicite dans le message, sinon résolution alias/friendly_name."""
    m = _ENT_PAT.search(msg)
    if m:
        eid = m.group(0).lower()
        return [eid], eid
    return await resolve_entities(msg)


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
            default_permissions=["ha:read", "ha:write"],
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        msg = request.message
        is_question = bool(_QUESTION_PAT.search(msg))

        if not is_question:
            # ── Consigne de température ───────────────────────────────────
            temp_resp = await self._maybe_set_temperature(request, msg)
            if temp_resp is not None:
                return temp_resp

            # ── Allumer / éteindre ────────────────────────────────────────
            is_off = bool(_OFF_PAT.search(msg))
            is_on  = bool(_ON_PAT.search(msg)) and not is_off
            if is_on or is_off:
                return await self._do_switch(request, msg, is_on)

        # ── Lecture : états ───────────────────────────────────────────────
        return await self._read_states(request, msg)

    async def _maybe_set_temperature(self, request: AgentRequest, msg: str) -> AgentResponse | None:
        """Retourne une réponse si le message est une consigne de température
        applicable à un thermostat, sinon None (on continue le traitement)."""
        temp_match = _TEMP_PAT.search(msg)
        if not (temp_match and _TEMP_VERBS.search(msg)):
            return None
        raw = (temp_match.group(1) or temp_match.group(2) or "").replace(",", ".")
        try:
            temperature = float(raw)
        except ValueError:
            return None
        if not (5 <= temperature <= 35):
            return None

        entity_ids, target = await _resolve_target(msg)
        heat_ids = [e for e in entity_ids
                    if e.split(".")[0] in ("climate", "water_heater")]
        if not heat_ids:
            # Pas un thermostat → ce n'était pas une consigne, on laisse
            # les autres branches (on/off, lecture) traiter le message.
            return None

        result = await set_temperature(
            heat_ids if len(heat_ids) > 1 else heat_ids[0], temperature)
        if result.ok:
            shown = ", ".join(f"`{e}`" for e in heat_ids)
            return AgentResponse(
                request_id=request.request_id,
                agent="home_assistant",
                status=AgentStatus.ok,
                content=f"✓ Consigne réglée à **{temperature}°C** sur {target} ({shown}).",
            )
        return AgentResponse(
            request_id=request.request_id,
            agent="home_assistant",
            status=AgentStatus.error,
            content=f"Erreur lors du réglage : {result.error}",
        )

    async def _do_switch(self, request: AgentRequest, msg: str, is_on: bool) -> AgentResponse:
        fn    = turn_on if is_on else turn_off
        label = "allumé" if is_on else "éteint"

        entity_ids, target = await _resolve_target(msg)
        if not entity_ids:
            return AgentResponse(
                request_id=request.request_id,
                agent="home_assistant",
                status=AgentStatus.ok,
                content=(
                    "Je n'ai pas trouvé à quelle entité tu fais référence. "
                    "Tu peux :\n"
                    "- préciser le nom exact (ex. « allume light.luminaire_salon »),\n"
                    "- ou déclarer un alias dans `config/ha_aliases.yaml`.\n\n"
                    "_Astuce : demande « liste les lumières » pour voir les noms réels._"
                ),
            )

        # Un seul appel de service — HA accepte une liste d'entity_id.
        result = await fn(entity_ids if len(entity_ids) > 1 else entity_ids[0])

        shown = ", ".join(f"`{e}`" for e in entity_ids[:6])
        extra = f" (+{len(entity_ids) - 6})" if len(entity_ids) > 6 else ""
        if not result.ok:
            return AgentResponse(
                request_id=request.request_id,
                agent="home_assistant",
                status=AgentStatus.error,
                content=f"Erreur sur {target} : {result.error}",
            )
        return AgentResponse(
            request_id=request.request_id,
            agent="home_assistant",
            status=AgentStatus.ok,
            content=f"✓ **{target}** {label} — {shown}{extra}",
        )

    async def _read_states(self, request: AgentRequest, msg: str) -> AgentResponse:
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
