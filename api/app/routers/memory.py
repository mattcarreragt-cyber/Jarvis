"""Endpoints mémoire — liste / ajout / suppression des faits durables."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import require_api_key
from app.memory import facts

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("", dependencies=[Depends(require_api_key)])
async def list_memory():
    return {"facts": await facts.list_facts(limit=200)}


class FactIn(BaseModel):
    text: str
    kind: str = "fact"


@router.post("", dependencies=[Depends(require_api_key)])
async def add_memory(body: FactIn):
    ok = await facts.add_fact(body.text, kind=body.kind)
    return {"ok": ok}


@router.delete("/{fact_id}", dependencies=[Depends(require_api_key)])
async def delete_memory(fact_id: str):
    return {"ok": await facts.delete_fact(fact_id)}


@router.delete("", dependencies=[Depends(require_api_key)])
async def clear_memory():
    return {"deleted": await facts.clear_facts()}
