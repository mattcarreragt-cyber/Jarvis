"""Galerie média durable — images & vidéos générées (Postgres).

Chaque rendu (image SDXL, vidéo AnimateDiff/SVD…) est enregistré ici pour être
retrouvé et téléchargé depuis le dashboard. view_url est construit vers les proxys
existants (/api/images/view, /api/video/view) avec le src RunPod si applicable.

Dégradation gracieuse : sans Postgres, tout renvoie vide / no-op.
"""

from __future__ import annotations

import logging
import uuid
from urllib.parse import urlencode

from app.db import get_pool

logger = logging.getLogger("jarvis.gallery")


def _view_url(kind: str, filename: str, subfolder: str, type_: str, base_url: str | None) -> str:
    params = {"filename": filename, "subfolder": subfolder, "type": type_}
    if base_url:
        params["src"] = base_url
    endpoint = "/api/images/view" if kind == "image" else "/api/video/view"
    return f"{endpoint}?{urlencode(params)}"


async def add_asset(kind: str, filename: str, subfolder: str = "", type_: str = "output",
                    prompt: str | None = None, base_url: str | None = None) -> str | None:
    pool = await get_pool()
    if pool is None:
        return None
    aid = str(uuid.uuid4())
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO media_assets(id,kind,prompt,filename,subfolder,type,base_url) "
                "VALUES($1,$2,$3,$4,$5,$6,$7)",
                aid, kind, prompt, filename, subfolder, type_, base_url)
        return aid
    except Exception as e:
        logger.warning("add_asset: %s", e)
        return None


async def list_assets(limit: int = 200, kind: str | None = None) -> list[dict]:
    pool = await get_pool()
    if pool is None:
        return []
    q = "SELECT id,kind,prompt,filename,subfolder,type,base_url,created_at FROM media_assets"
    args: list = []
    if kind:
        q += " WHERE kind = $2"
        args.append(kind)
    q += " ORDER BY created_at DESC LIMIT $1"
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(q, limit, *args)
        return [{
            "id": r["id"], "kind": r["kind"], "prompt": r["prompt"],
            "created_at": r["created_at"].isoformat(),
            "view_url": _view_url(r["kind"], r["filename"], r["subfolder"], r["type"], r["base_url"]),
        } for r in rows]
    except Exception as e:
        logger.warning("list_assets: %s", e)
        return []


async def delete_asset(asset_id: str) -> bool:
    pool = await get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            res = await conn.execute("DELETE FROM media_assets WHERE id=$1", asset_id)
        return res.endswith("1")
    except Exception as e:
        logger.warning("delete_asset: %s", e)
        return False
