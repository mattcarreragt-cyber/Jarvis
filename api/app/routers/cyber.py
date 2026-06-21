"""Endpoints cybersécurité — inventaire d'hôtes, audit, remédiation explicite."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_api_key
from app.cyber import audit, ssh, store

router = APIRouter(prefix="/api/cyber", tags=["cyber"])


class HostIn(BaseModel):
    label: str
    hostname: str
    username: str
    port: int = 22


@router.get("/hosts", dependencies=[Depends(require_api_key)])
async def list_hosts():
    return {"hosts": await store.list_hosts()}


@router.post("/hosts", dependencies=[Depends(require_api_key)])
async def add_host(body: HostIn):
    h = await store.add_host(body.label, body.hostname, body.username, body.port)
    if h is None:
        raise HTTPException(503, "Base indisponible ou label déjà pris")
    return h


@router.delete("/hosts/{host_id}", dependencies=[Depends(require_api_key)])
async def delete_host(host_id: str):
    return {"ok": await store.delete_host(host_id)}


@router.post("/hosts/{host_id}/audit", dependencies=[Depends(require_api_key)])
async def run_audit(host_id: str):
    host = await store.get_host(host_id)
    if host is None:
        raise HTTPException(404, "Hôte inconnu")
    result = await audit.run_audit(host)
    if result.get("ok"):
        await store.save_findings(host["id"], result["findings"])
        if result.get("score") is not None:
            await store.save_score(host["id"], result["score"], result.get("grade", "?"))
    return result


@router.get("/hosts/{host_id}/findings", dependencies=[Depends(require_api_key)])
async def findings(host_id: str):
    return {"findings": await store.latest_findings(host_id)}


@router.get("/hosts/{host_id}/scores", dependencies=[Depends(require_api_key)])
async def scores(host_id: str):
    return {"history": await store.score_history(host_id)}


class RemediateIn(BaseModel):
    command: str


@router.post("/hosts/{host_id}/remediate", dependencies=[Depends(require_api_key)])
async def remediate(host_id: str, body: RemediateIn):
    """Exécute une commande de remédiation SSH (action explicite de l'utilisateur)."""
    host = await store.get_host(host_id)
    if host is None:
        raise HTTPException(404, "Hôte inconnu")
    result = await ssh.run_once(host, body.command)
    if not result.get("ok"):
        raise HTTPException(502, result.get("error", "Échec SSH"))
    return result
