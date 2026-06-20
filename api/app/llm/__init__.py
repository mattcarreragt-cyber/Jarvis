"""Couche LLM locale (Ollama sur Kubuntu) — embeddings + chat + synthèse RAG."""

from app.llm.ollama import (
    CHAT_MODEL_DEEP,
    CHAT_MODEL_FAST,
    EMBED_DIM,
    EMBED_MODEL,
    chat,
    embed,
    embed_batch,
    health,
)
from app.llm.rag import synthesize

__all__ = [
    "embed",
    "embed_batch",
    "chat",
    "health",
    "synthesize",
    "EMBED_DIM",
    "EMBED_MODEL",
    "CHAT_MODEL_FAST",
    "CHAT_MODEL_DEEP",
]
