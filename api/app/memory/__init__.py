"""Couche mémoire — assemble court terme (Redis) + long terme (Qdrant).

build_context() construit le MemoryContext injecté dans chaque AgentRequest.
Tout est tolérant aux pannes : un service absent n'empêche pas le chat.
"""

from __future__ import annotations

from app.contracts import MemoryContext, Turn
from app.memory import facts
from app.memory.long_term import LongTermMemory
from app.memory.short_term import ShortTermMemory


class Memory:
    def __init__(
        self,
        short: ShortTermMemory | None = None,
        long: LongTermMemory | None = None,
    ) -> None:
        self.short = short or ShortTermMemory()
        self.long = long or LongTermMemory()

    async def build_context(self, session_id: str, message: str) -> MemoryContext:
        recent = await self.short.recent(session_id)
        # Faits durables (Postgres, toujours dispo) + rappel sémantique (Qdrant/Ollama)
        durable = await facts.search_facts(message)
        semantic = await self.long.recall(message)
        # Fusion sans doublons, faits durables d'abord
        merged: list[str] = []
        for m in durable + semantic:
            if m and m not in merged:
                merged.append(m)
        return MemoryContext(
            recent_turns=recent,
            relevant_memories=merged,
            user_profile={},
        )

    async def record_turn(self, session_id: str, role: str, content: str,
                          agent: str | None = None) -> None:
        await self.short.append(
            session_id, Turn(role=role, content=content, agent=agent)
        )


memory = Memory()

__all__ = ["Memory", "memory", "ShortTermMemory", "LongTermMemory"]
