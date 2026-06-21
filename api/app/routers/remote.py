"""Endpoints bureau distant (streaming) + VPN."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import require_api_key
from app.remote import stream
from app.vpn import mullvad

router = APIRouter(prefix="/api", tags=["remote"])


@router.get("/remote/status", dependencies=[Depends(require_api_key)])
async def remote_status():
    return {"sunshine_up": await stream.is_sunshine_up(), "host": stream.kubuntu_host()}


@router.post("/remote/wake", dependencies=[Depends(require_api_key)])
async def remote_wake():
    return await stream.wake_and_wait()


@router.get("/vpn/status", dependencies=[Depends(require_api_key)])
async def vpn_status():
    ssh = await mullvad.ssh_status()
    return {"ssh_status": ssh, "http_status": await mullvad.http_status()}


class VpnControl(BaseModel):
    action: str               # connect | disconnect | location
    location: str | None = None


@router.post("/vpn/control", dependencies=[Depends(require_api_key)])
async def vpn_control(body: VpnControl):
    return await mullvad.control(body.action, body.location)
