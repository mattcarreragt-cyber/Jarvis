"""Tests mémoire — assemblage du contexte + dégradation gracieuse (étape 5)."""

from app.contracts import MemoryContext, Turn
from app.memory import Memory


class _FakeShort:
    def __init__(self):
        self.store: dict[str, list[Turn]] = {}

    async def append(self, session_id, turn):
        self.store.setdefault(session_id, []).append(turn)

    async def recent(self, session_id, limit=20):
        return self.store.get(session_id, [])[-limit:]


class _FakeLong:
    def __init__(self, memories=None):
        self.memories = memories or []

    async def recall(self, query, top_k=3):
        return self.memories[:top_k]


async def test_build_context_assembles_sources():
    short = _FakeShort()
    await short.append("s1", Turn(role="user", content="salut"))
    mem = Memory(short=short, long=_FakeLong(["préfère le français"]))

    ctx = await mem.build_context("s1", "bonjour")
    assert isinstance(ctx, MemoryContext)
    assert ctx.recent_turns[0].content == "salut"
    assert ctx.relevant_memories == ["préfère le français"]


async def test_record_turn_persists():
    short = _FakeShort()
    mem = Memory(short=short, long=_FakeLong())
    await mem.record_turn("s1", "user", "test", agent=None)
    await mem.record_turn("s1", "assistant", "ok", agent="echo")

    ctx = await mem.build_context("s1", "x")
    assert len(ctx.recent_turns) == 2
    assert ctx.recent_turns[1].agent == "echo"


async def test_graceful_when_no_services():
    # Pas de Redis/Qdrant : doit renvoyer un contexte vide, pas planter.
    mem = Memory(short=_FakeShort(), long=_FakeLong([]))
    ctx = await mem.build_context("unknown", "hello")
    assert ctx.recent_turns == []
    assert ctx.relevant_memories == []
