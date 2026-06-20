"""État de synchronisation Nextcloud en Postgres (table nextcloud_files).

Dégradation gracieuse : sans Postgres, la sync re-ingère tout à chaque passage
(pas d'incrémental) mais ne casse pas.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.db import get_pool

logger = logging.getLogger("jarvis.ncstate")


async def known_etags() -> dict[str, str]:
    """Retourne {path: etag} des fichiers déjà ingérés."""
    pool = await get_pool()
    if pool is None:
        return {}
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT path, etag FROM nextcloud_files")
        return {r["path"]: r["etag"] for r in rows}
    except Exception as e:
        logger.warning("known_etags: %s", e)
        return {}


async def upsert_file(path: str, etag: str, chunks: int) -> None:
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO nextcloud_files(path, etag, chunks, synced_at) "
                "VALUES($1,$2,$3,$4) "
                "ON CONFLICT(path) DO UPDATE SET etag=$2, chunks=$3, synced_at=$4",
                path, etag, chunks, datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.warning("upsert_file: %s", e)


async def remove_file(path: str) -> None:
    pool = await get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM nextcloud_files WHERE path=$1", path)
    except Exception as e:
        logger.warning("remove_file: %s", e)


async def stats() -> dict:
    pool = await get_pool()
    if pool is None:
        return {"files": 0, "chunks": 0, "last_sync": None}
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS files, COALESCE(SUM(chunks),0) AS chunks, "
                "MAX(synced_at) AS last_sync FROM nextcloud_files"
            )
        return {
            "files": row["files"],
            "chunks": row["chunks"],
            "last_sync": row["last_sync"].isoformat() if row["last_sync"] else None,
        }
    except Exception as e:
        logger.warning("stats: %s", e)
        return {"files": 0, "chunks": 0, "last_sync": None}
