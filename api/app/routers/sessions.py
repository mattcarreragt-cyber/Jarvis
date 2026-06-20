"""Endpoints historique des sessions."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
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
