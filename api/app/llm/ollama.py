"""Client Ollama — embeddings + chat, hébergé sur Kubuntu (GPU).

Best-effort : si Kubuntu/Ollama est injoignable, toutes les fonctions renvoient
None (embeddings) ou None (chat). Les appelants retombent alors sur le mode keyword
/ extraits bruts. Aucun réveil Wake-on-LAN n'est déclenché ici — on respecte le fait
que Kubuntu peut dormir. Le réveil explicite passe par app.orchestration.scheduler.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger("jarvis.llm")

EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768                     # dimension de nomic-embed-text
CHAT_MODEL_FAST = "llama3.1:8b"
CHAT_MODEL_DEEP = "llama3.1:70b"

_EMBED_TIMEOUT = 15
_CHAT_TIMEOUT = 120


def _base() -> str:
    return settings.ollama_base_url.rstrip("/")


async def health() -> bool:
    """True si Ollama répond (Kubuntu en ligne)."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{_base()}/api/tags")
            return r.status_code < 500
    except Exception:
        return False


async def embed(text: str, model: str = EMBED_MODEL) -> list[float] | None:
    """Embedding d'un texte. None si Ollama injoignable."""
    if not text.strip():
        return None
    try:
        async with httpx.AsyncClient(timeout=_EMBED_TIMEOUT) as client:
            r = await client.post(
                f"{_base()}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            r.raise_for_status()
            return r.json()["embedding"]
    except Exception as e:
        logger.debug("embed indisponible (Kubuntu éteint ?): %s", e)
        return None


async def embed_batch(texts: list[str], model: str = EMBED_MODEL) -> list[list[float] | None]:
    """Embeddings séquentiels (Ollama n'a pas d'endpoint batch natif stable).

    Court-circuite dès le premier échec de connexion : si Ollama est down,
    inutile d'attendre le timeout sur chaque chunk.
    """
    out: list[list[float] | None] = []
    available = True
    for t in texts:
        if not available:
            out.append(None)
            continue
        v = await embed(t, model)
        if v is None:
            available = False
        out.append(v)
    return out


async def chat(
    messages: list[dict],
    model: str = CHAT_MODEL_FAST,
    temperature: float = 0.7,
) -> str | None:
    """Complétion de chat. messages = [{"role": "...", "content": "..."}].

    None si Ollama injoignable.
    """
    try:
        async with httpx.AsyncClient(timeout=_CHAT_TIMEOUT) as client:
            r = await client.post(
                f"{_base()}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
            )
            r.raise_for_status()
            return r.json().get("message", {}).get("content", "").strip() or None
    except Exception as e:
        logger.debug("chat indisponible (Kubuntu éteint ?): %s", e)
        return None
