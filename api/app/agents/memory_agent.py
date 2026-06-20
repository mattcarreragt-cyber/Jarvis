"""Agent Mémoire — retenir / rappeler / oublier des faits durables.

Stocke en Postgres (durable, sans Ollama) et, si les embeddings sont dispo,
réplique dans la mémoire sémantique Qdrant pour un rappel plus fin.
"""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult
from app.memory import facts

# « souviens-toi que X », « retiens X », « note que X », « mémorise X »
_REMEMBER = re.compile(
    r"\b(?:souviens[-\s]?toi|retiens|rappelle[-\s]?toi|mémorise|memorise|note)\s+"
    r"(?:que\s+|de\s+|:\s*)?(.+)", re.I,
)
_FORGET_ALL = re.compile(r"\b(oublie|efface|supprime)\s+(tout|tous|toutes)\b", re.I)
_RECALL = re.compile(
    r"\b(que\s+sais[-\s]?tu|qu'est[-\s]?ce\s+que\s+tu\s+sais|mes\s+infos?|"
    r"mon\s+profil|tes\s+souvenirs|liste.*souvenirs)\b", re.I,
)


class MemoryAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="memoire",
            description="Mémoire long terme : retenir des faits, rappeler ce qui est "
                        "mémorisé, oublier. Préférences et profil de l'utilisateur.",
            keywords=[
                "souviens", "souviens-toi", "retiens", "rappelle-toi", "mémorise",
                "memorise", "oublie", "efface", "profil", "souvenirs", "mémoire",
            ],
            default_permissions=["memory:write"],
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        msg = req.message.strip()

        # ── Oublier tout ──────────────────────────────────────────────────
        if _FORGET_ALL.search(msg):
            n = await facts.clear_facts()
            return self._resp(req, f"🧹 Mémoire effacée ({n} fait{'s' if n != 1 else ''} supprimé"
                                   f"{'s' if n != 1 else ''}).",
                              ToolCall(tool="memory.clear", args={},
                                       result=ToolResult(ok=True, data={"deleted": n})))

        # ── Rappeler / lister ─────────────────────────────────────────────
        if _RECALL.search(msg):
            items = await facts.list_facts(limit=30)
            if not items:
                return self._resp(req, "Je n'ai encore rien mémorisé sur toi. "
                                       "Dis « souviens-toi que… » pour commencer.",
                                  ToolCall(tool="memory.list", args={},
                                           result=ToolResult(ok=True, data={"count": 0})))
            lines = ["## Ce que j'ai mémorisé", ""]
            lines += [f"- {it['text']}" for it in items]
            return self._resp(req, "\n".join(lines),
                              ToolCall(tool="memory.list", args={},
                                       result=ToolResult(ok=True, data={"count": len(items)})))

        # ── Retenir un fait ───────────────────────────────────────────────
        m = _REMEMBER.search(msg)
        if m:
            fact = m.group(1).strip(" .")
            ok = await facts.add_fact(fact, session_id=req.session_id)
            # Réplique best-effort dans Qdrant sémantique (si embeddings dispo)
            try:
                from app.memory.long_term import LongTermMemory
                await LongTermMemory().remember(fact, session_id=req.session_id)
            except Exception:
                pass
            content = (f"✓ C'est noté : *{fact}*" if ok
                       else "Je n'ai pas pu enregistrer (base mémoire indisponible).")
            return self._resp(req, content,
                              ToolCall(tool="memory.add", args={"text": fact},
                                       result=ToolResult(ok=ok)),
                              status=AgentStatus.ok if ok else AgentStatus.error)

        # ── Sinon : aide ──────────────────────────────────────────────────
        return self._resp(req,
            "Mémoire JARVIS :\n"
            "- **Retenir** : « souviens-toi que je préfère le café noir »\n"
            "- **Rappeler** : « que sais-tu sur moi ? »\n"
            "- **Oublier** : « oublie tout »",
            ToolCall(tool="memory.help", args={}, result=ToolResult(ok=True)))

    @staticmethod
    def _resp(req: AgentRequest, content: str, call: ToolCall,
              status: AgentStatus = AgentStatus.ok) -> AgentResponse:
        return AgentResponse(request_id=req.request_id, agent="memoire",
                             status=status, content=content, tool_calls=[call])
