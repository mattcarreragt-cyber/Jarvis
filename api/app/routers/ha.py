"""Endpoints Home Assistant — états/capteurs + bascule (action explicite)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agents.ha_tools import get_states, turn_off, turn_on
from app.auth import require_api_key

router = APIRouter(prefix="/api/ha", tags=["home_assistant"])


@router.get("/states", dependencies=[Depends(require_api_key)])
async def states(domain: str | None = None):
    """États HA (capteurs, lumières, switches…), filtrés par domaine si fourni."""
    res = await get_states(domain=domain)
    if not res.ok:
        raise HTTPException(502, res.error or "Home Assistant injoignable")
    return res.data


class Toggle(BaseModel):
    entity_id: str
    on: bool


@router.post("/toggle", dependencies=[Depends(require_api_key)])
async def toggle(body: Toggle):
    """Allume/éteint une entité (le clic du dashboard = action explicite)."""
    res = await (turn_on(body.entity_id) if body.on else turn_off(body.entity_id))
    if not res.ok:
        raise HTTPException(502, res.error or "Action HA échouée")
    return {"ok": True, "entity_id": body.entity_id, "on": body.on}
