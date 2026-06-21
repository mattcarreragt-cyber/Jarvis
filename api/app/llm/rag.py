"""Synthèse RAG — transforme des extraits récupérés en réponse rédigée.

Best-effort : si le LLM (Kubuntu) est injoignable, retourne None et l'agent
retombe sur l'affichage des extraits bruts.
"""

from __future__ import annotations

from app.llm.ollama import CHAT_MODEL_FAST, chat
from app.llm.persona import rag_system


def _format_context(hits: list[dict]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        src = h.get("source", "?").split("nextcloud:", 1)[-1]
        blocks.append(f"[{i}] (source: {src})\n{h.get('text', '').strip()}")
    return "\n\n".join(blocks)


async def synthesize(
    question: str,
    hits: list[dict],
    model: str = CHAT_MODEL_FAST,
) -> str | None:
    """Génère une réponse rédigée à partir des extraits. None si LLM indisponible."""
    if not hits:
        return None
    context = _format_context(hits)
    messages = [
        {"role": "system", "content": rag_system()},
        {"role": "user", "content": f"Extraits :\n\n{context}\n\nQuestion : {question}"},
    ]
    return await chat(messages, model=model, temperature=0.3)
