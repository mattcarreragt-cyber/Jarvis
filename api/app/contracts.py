"""Contrats de données JARVIS OS — voir docs/02_CONTRACTS.md.

Ces modèles sont les interfaces stables entre Dashboard, API, Router,
Agents et Outils. Toute couche les respecte.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ─── Énumérations ───────────────────────────────────────────────────────────

class Modality(str, Enum):
    text = "text"
    voice = "voice"


class SideEffect(str, Enum):
    none = "none"
    read = "read"
    write = "write"


class AgentStatus(str, Enum):
    ok = "ok"
    error = "error"
    queued = "queued"
    needs_confirmation = "needs_confirmation"


# ─── Entrée Dashboard → API ─────────────────────────────────────────────────

class Attachment(BaseModel):
    kind: str                       # "image", "document", "audio"...
    name: str
    url: str | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str
    modality: Modality = Modality.text
    attachments: list[Attachment] = Field(default_factory=list)
    force_agent: str | None = None  # bypass router (debug/avancé)


# ─── Mémoire (voir docs/04_MEMORY.md) ───────────────────────────────────────

class Turn(BaseModel):
    role: str                       # "user" | "assistant"
    content: str
    agent: str | None = None


class MemoryContext(BaseModel):
    recent_turns: list[Turn] = Field(default_factory=list)
    relevant_memories: list[str] = Field(default_factory=list)
    user_profile: dict[str, Any] = Field(default_factory=dict)


# ─── Outils ─────────────────────────────────────────────────────────────────

class ToolResult(BaseModel):
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class ToolCall(BaseModel):
    """Trace d'un appel d'outil exécuté par un agent."""
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: ToolResult | None = None


class ToolSpec(BaseModel):
    """Descripteur statique d'un outil (sans le handler, qui vit côté code)."""
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)  # JSON Schema
    required_permissions: list[str] = Field(default_factory=list)
    side_effects: SideEffect = SideEffect.none


# ─── Agents ─────────────────────────────────────────────────────────────────

class AgentSpec(BaseModel):
    """Descripteur statique d'un agent, lu par le Router."""
    name: str
    description: str                # utilisée par le router LLM
    keywords: list[str] = Field(default_factory=list)  # router à règles
    tools: list[ToolSpec] = Field(default_factory=list)
    default_permissions: list[str] = Field(default_factory=list)


class Artifact(BaseModel):
    kind: str                       # "image", "file", "audio"...
    name: str
    url: str | None = None
    data: dict[str, Any] | None = None


class ConfirmationRequest(BaseModel):
    """Émise quand un outil 'write' sur un système en prod doit être confirmé."""
    request_id: str
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    summary: str                    # ce qui va se passer, en clair


class AgentRequest(BaseModel):
    request_id: str
    session_id: str
    intent: str
    message: str
    context: MemoryContext = Field(default_factory=MemoryContext)
    permissions: list[str] = Field(default_factory=list)
    hint: str | None = None         # "fast" | "deep" — voir Scheduler


class AgentResponse(BaseModel):
    request_id: str
    agent: str
    status: AgentStatus = AgentStatus.ok
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    confirmation: ConfirmationRequest | None = None


# ─── Routage (traçabilité) ──────────────────────────────────────────────────

class RouteDecision(BaseModel):
    agent: str
    method: str                     # "rules" | "llm" | "forced"
    score: float | None = None
