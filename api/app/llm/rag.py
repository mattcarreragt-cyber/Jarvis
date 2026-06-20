"""Synthèse RAG — transforme des extraits récupérés en réponse rédigée.

Best-effort : si le LLM (Kubuntu) est injoignable, retourne None et l'agent
retombe sur l'affichage des extraits bruts.
"""

from __future__ import annotations

from app.llm.ollama import CHAT_MODEL_FAST, chat

_SYSTEM = (
    "Tu es JARVIS, un assistant local. Réponds en français, de façon concise et "
    "factuelle, en t'appuyant UNIQUEMENT sur les extraits fournis. Cite les sources "
    "entre crochets, ex. [1]. Si les extraits ne suffisent pas, dis-le clairement "
    "sans inventer."
)


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
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"Extraits :\n\n{context}\n\nQuestion : {question}"},
    ]
    return await chat(messages, model=model, temperature=0.3)
