"""Endpoints historique des sessions."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth import require_api_key
from app.db import get_pool

logger = logging.getLogger("jarvis.sessions")
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionSummary(BaseModel):
    id: str
    created_at: str
    title: str | None
    message_count: int


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    agent: str | None
    created_at: str


@router.get("", response_model=list[SessionSummary])
async def list_sessions(_: str = Depends(require_api_key)):
    pool = await get_pool()
    if pool is None:
        raise HTTPException(503, "Base de données indisponible")
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT s.id, s.created_at, s.title,
                   COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id, s.created_at, s.title
            ORDER BY s.created_at DESC
            LIMIT 50
        """)
    return [
        SessionSummary(
            id=r["id"],
            created_at=str(r["created_at"]),
            title=r["title"],
            message_count=r["message_count"],
        )
        for r in rows
    ]


@router.get("/{session_id}", response_model=list[MessageOut])
async def get_session(session_id: str, _: str = Depends(require_api_key)):
    pool = await get_pool()
    if pool is None:
        raise HTTPException(503, "Base de données indisponible")
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, role, content, agent, created_at
            FROM messages
            WHERE session_id = $1
            ORDER BY created_at ASC
        """, session_id)
    if not rows:
        raise HTTPException(404, "Session introuvable")
    return [
        MessageOut(
            id=r["id"],
            role=r["role"],
            content=r["content"],
            agent=r["agent"],
            created_at=str(r["created_at"]),
        )
        for r in rows
    ]


async def _fetch_messages(session_id: str) -> list[dict]:
    pool = await get_pool()
    if pool is None:
        raise HTTPException(503, "Base de données indisponible")
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT role, content, agent, created_at FROM messages "
            "WHERE session_id = $1 ORDER BY created_at ASC", session_id)
    if not rows:
        raise HTTPException(404, "Session introuvable")
    return [{"role": r["role"], "content": r["content"], "agent": r["agent"],
             "created_at": str(r["created_at"])} for r in rows]


def _to_markdown(session_id: str, msgs: list[dict]) -> str:
    lines = [f"# Conversation JARVIS — {session_id[:8]}", ""]
    if msgs:
        lines.append(f"_Du {msgs[0]['created_at'][:16]} au {msgs[-1]['created_at'][:16]}_")
        lines.append("")
    for m in msgs:
        if m["role"] == "user":
            who = "🧑 **Vous**"
        else:
            who = f"🤖 **JARVIS** _[{m['agent']}]_" if m.get("agent") else "🤖 **JARVIS**"
        lines.append(f"### {who}")
        lines.append(m["content"])
        lines.append("")
    return "\n".join(lines)


@router.get("/{session_id}/export", dependencies=[Depends(require_api_key)])
async def export_session(session_id: str, format: str = "md"):
    """Exporte une conversation en Markdown (défaut) ou JSON, en téléchargement."""
    msgs = await _fetch_messages(session_id)
    short = session_id[:8]
    if format == "json":
        body = json.dumps({"session_id": session_id, "messages": msgs},
                          ensure_ascii=False, indent=2)
        return Response(
            content=body, media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="jarvis_{short}.json"'})
    md = _to_markdown(session_id, msgs)
    return Response(
        content=md, media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="jarvis_{short}.md"'})
