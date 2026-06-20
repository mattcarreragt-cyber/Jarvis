"""Orchestration layer: WoL + Capability Scheduler."""

from app.orchestration.scheduler import dispatch, get_capability, reload, resolve_chat_hint
from app.orchestration.wol import ensure_kubuntu, is_kubuntu_alive, send_magic_packet

__all__ = [
    "dispatch",
    "get_capability",
    "reload",
    "resolve_chat_hint",
    "ensure_kubuntu",
    "is_kubuntu_alive",
    "send_magic_packet",
]
