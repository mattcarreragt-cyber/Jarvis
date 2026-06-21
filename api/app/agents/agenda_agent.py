"""Agent Agenda — rappels et automatisations planifiées en langage naturel.

Exemples :
- « rappelle-moi d'appeler le client à 14h30 »          → once, reminder
- « dans 20 minutes, sortir le gâteau »                  → once, reminder
- « chaque jour à 8h, résume mes nouveaux fichiers »     → daily, prompt
- « toutes les 2 heures, vérifie l'espace disque »       → interval, prompt
- « mes rappels »  /  « annule tout »
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from app.agents.base import Agent
from app.automation import store
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult

_TIME = re.compile(r"\bà\s+(\d{1,2})\s*[h:]\s*(\d{2})?", re.I)
_DELAY = re.compile(r"\bdans\s+(\d+)\s*(secondes?|sec|minutes?|min|heures?|h)\b", re.I)
_INTERVAL = re.compile(r"\btoutes?\s+les\s+(\d+)\s*(secondes?|sec|minutes?|min|heures?|h)\b", re.I)
_DAILY = re.compile(r"\b(chaque\s+jour|tous\s+les\s+jours|quotidien)\b", re.I)
_LIST = re.compile(r"\b(mes\s+rappels|mes\s+t[âa]ches|mon\s+agenda|liste.*rappels)\b", re.I)
_CLEAR = re.compile(r"\b(annule|efface|supprime)\s+(tout|tous|toutes|les\s+rappels)\b", re.I)
_COMMAND = re.compile(
    r"\b(résume|resume|cherche|trouve|génère|genere|analyse|liste|calcule|"
    r"transcris|vérifie|verifie|surveille|rapporte)\b", re.I,
)
_STRIP = re.compile(
    r"\b(rappelle[-\s]?moi|rappel|planifie|programme|automatise|chaque\s+jour|"
    r"tous\s+les\s+jours|quotidien|d'|de\s|que\s|:)\b", re.I,
)


def _unit_seconds(n: int, unit: str) -> int:
    u = unit.lower()
    if u.startswith("h"):
        return n * 3600
    if u.startswith("min") or u == "min":
        return n * 60
    return n   # secondes


class AgendaAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="agenda",
            description="Rappels et automatisations planifiées : rappels horaires, "
                        "tâches récurrentes (quotidiennes / par intervalle), notifications.",
            keywords=[
                "rappelle", "rappelle-moi", "rappel", "rappels", "planifie",
                "programme", "agenda", "automatise", "chaque jour", "tous les jours",
                "quotidien", "notifie", "tâche planifiée",
            ],
            default_permissions=["agenda:write"],
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        msg = req.message.strip()

        if _CLEAR.search(msg):
            n = await store.clear_tasks()
            return self._r(req, f"🗑️ {n} tâche(s) supprimée(s).", "agenda.clear", {"deleted": n})

        if _LIST.search(msg):
            tasks = await store.list_tasks()
            if not tasks:
                return self._r(req, "Aucun rappel ni tâche planifiée.", "agenda.list", {"count": 0})
            lines = ["## Mes rappels & tâches", ""]
            for t in tasks:
                when = self._describe(t)
                state = "" if t["enabled"] else " _(terminé)_"
                lines.append(f"- **{t['payload']}** — {when}{state}")
            return self._r(req, "\n".join(lines), "agenda.list", {"count": len(tasks)})

        parsed = self._parse_schedule(msg)
        if parsed is None:
            return self._r(req,
                "Agenda JARVIS :\n"
                "- « rappelle-moi d'appeler Paul **à 14h30** »\n"
                "- « **dans 20 minutes**, sortir le plat »\n"
                "- « **chaque jour à 8h**, résume mes nouveaux fichiers »\n"
                "- « **toutes les 2 heures**, vérifie l'espace disque »\n"
                "- « mes rappels » · « annule tout »",
                "agenda.help", {})

        kind = "prompt" if _COMMAND.search(parsed["payload"]) else "reminder"
        tid = await store.add_task(
            label=parsed["payload"][:80], kind=kind, payload=parsed["payload"],
            schedule_kind=parsed["schedule_kind"], next_run=parsed["next_run"],
            time_of_day=parsed.get("time_of_day"), interval_sec=parsed.get("interval_sec"),
        )
        if tid is None:
            return self._r(req, "Impossible d'enregistrer (base agenda indisponible).",
                           "agenda.add", {}, status=AgentStatus.error)

        when = self._describe(parsed)
        emoji = "🤖" if kind == "prompt" else "⏰"
        return self._r(req, f"{emoji} C'est planifié : **{parsed['payload']}** — {when}.",
                       "agenda.add", {"id": tid, "kind": kind})

    # ── Parsing ──────────────────────────────────────────────────────────────

    def _parse_schedule(self, msg: str) -> dict | None:
        now = datetime.now(timezone.utc)
        interval = _INTERVAL.search(msg)
        delay = _DELAY.search(msg)
        time_m = _TIME.search(msg)
        daily = _DAILY.search(msg)

        payload = self._extract_payload(msg)
        if not payload:
            return None

        if interval:
            sec = _unit_seconds(int(interval.group(1)), interval.group(2))
            return {"payload": payload, "schedule_kind": "interval",
                    "interval_sec": sec, "next_run": now + timedelta(seconds=sec)}

        if daily and time_m:
            tod = self._time_str(time_m)
            return {"payload": payload, "schedule_kind": "daily", "time_of_day": tod,
                    "next_run": store.compute_next_run("daily", tod, None, now)}

        if delay:
            sec = _unit_seconds(int(delay.group(1)), delay.group(2))
            return {"payload": payload, "schedule_kind": "once",
                    "next_run": now + timedelta(seconds=sec)}

        if time_m:
            tod = self._time_str(time_m)
            return {"payload": payload, "schedule_kind": "once", "time_of_day": tod,
                    "next_run": store.compute_next_run("daily", tod, None, now)}

        return None

    @staticmethod
    def _time_str(m: re.Match) -> str:
        hh = int(m.group(1))
        mm = int(m.group(2)) if m.group(2) else 0
        return f"{hh:02d}:{mm:02d}"

    def _extract_payload(self, msg: str) -> str:
        s = _INTERVAL.sub(" ", msg)
        s = _DELAY.sub(" ", s)
        s = _TIME.sub(" ", s)
        s = _STRIP.sub(" ", s)
        s = re.sub(r"\s+", " ", s).strip(" ,.;:")
        return s

    @staticmethod
    def _describe(t: dict) -> str:
        sk = t["schedule_kind"]
        if sk == "daily":
            return f"chaque jour à {t.get('time_of_day')}"
        if sk == "interval":
            sec = t.get("interval_sec") or 0
            return f"toutes les {sec // 60} min" if sec >= 60 else f"toutes les {sec}s"
        nr = t["next_run"]
        nr = nr if isinstance(nr, str) else nr.isoformat()
        return f"le {nr[:16].replace('T', ' à ')}"

    @staticmethod
    def _r(req: AgentRequest, content: str, tool: str, data: dict,
           status: AgentStatus = AgentStatus.ok) -> AgentResponse:
        return AgentResponse(request_id=req.request_id, agent="agenda", status=status,
                             content=content,
                             tool_calls=[ToolCall(tool=tool, args={},
                                                  result=ToolResult(ok=status == AgentStatus.ok, data=data))])
