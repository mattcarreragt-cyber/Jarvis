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
CHAT_MODEL_FAST = "qwen2.5:7b"      # ~5 Go VRAM — tient sur 8 Go (100% GPU)
CHAT_MODEL_DEEP = "qwen2.5:14b"     # ~9 Go — offload CPU partiel (RAM 64 Go)

_EMBED_TIMEOUT = 15
_CHAT_TIMEOUT = 120


def _base(override: str | None = None) -> str:
    return (override or settings.ollama_base_url).rstrip("/")


async def health() -> bool:
    """True si Ollama répond (Kubuntu en ligne)."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{_base()}/api/tags")
            return r.status_code < 500
    except Exception:
        return False


async def ps() -> list[dict]:
    """Modèles actuellement chargés en VRAM par Ollama (GET /api/ps)."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{_base()}/api/ps")
            r.raise_for_status()
            return r.json().get("models", [])
    except Exception:
        return []


async def unload(model: str) -> bool:
    """Décharge un modèle de la VRAM (keep_alive=0)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{_base()}/api/generate",
                json={"model": model, "keep_alive": 0},
            )
            return r.status_code < 500
    except Exception as e:
        logger.debug("unload %s échoué: %s", model, e)
        return False


async def unload_all() -> int:
    """Décharge tous les modèles LLM chargés. Retourne le nombre déchargé."""
    models = await ps()
    n = 0
    for m in models:
        name = m.get("name") or m.get("model", "")
        if name and await unload(name):
            n += 1
    return n


async def embed(text: str, model: str = EMBED_MODEL,
                base_url: str | None = None) -> list[float] | None:
    """Embedding d'un texte. None si Ollama injoignable."""
    if not text.strip():
        return None
    try:
        async with httpx.AsyncClient(timeout=_EMBED_TIMEOUT) as client:
            r = await client.post(
                f"{_base(base_url)}/api/embeddings",
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
    base_url: str | None = None,
) -> str | None:
    """Complétion de chat. messages = [{"role": "...", "content": "..."}].

    base_url : surcharge l'endpoint (ex. RunPod). None = Kubuntu par défaut.
    None si Ollama injoignable.
    """
    try:
        async with httpx.AsyncClient(timeout=_CHAT_TIMEOUT) as client:
            r = await client.post(
                f"{_base(base_url)}/api/chat",
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
