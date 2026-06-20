"""Synchronisation incrémentale Nextcloud → Qdrant.

Algorithme :
1. Liste récursive des fichiers Nextcloud (walk_files).
2. Pour chaque fichier supporté et sous la limite de taille :
   - inchangé (même etag)  → skip
   - nouveau / modifié      → download, extract, ingest (replace), maj état
3. Fichiers connus absents du listing → supprimés côté NC → on purge Qdrant + état.

Verrou global : une seule sync à la fois (manuelle ou périodique).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.config import settings
from app.docs.extract import is_supported
from app.docs.ingest import delete_source, ingest_file
from app.sources import nextcloud, state

logger = logging.getLogger("jarvis.ncsync")

_lock = asyncio.Lock()
_last_result: dict | None = None
_running = False

SOURCE_PREFIX = "nextcloud:"


def _source_id(path: str) -> str:
    return f"{SOURCE_PREFIX}{path}"


def is_running() -> bool:
    return _running


def last_result() -> dict | None:
    return _last_result


async def sync() -> dict:
    """Lance une sync. Retourne un récap. Non-réentrant (verrou)."""
    global _last_result, _running

    if _lock.locked():
        return {"ok": False, "error": "Sync déjà en cours", "skipped": True}

    async with _lock:
        _running = True
        result = {
            "ok": True, "added": 0, "updated": 0, "skipped": 0,
            "removed": 0, "errors": [], "scanned": 0,
        }
        try:
            if not nextcloud._configured():
                return {"ok": False, "error": "Nextcloud non configuré"}

            remote = await nextcloud.walk_files()
            known = await state.known_etags()
            max_bytes = settings.nextcloud_max_file_mb * 1024 * 1024
            seen_paths: set[str] = set()

            for rf in remote:
                result["scanned"] += 1
                if not is_supported(rf.path):
                    continue
                seen_paths.add(rf.path)

                if rf.size > max_bytes:
                    result["errors"].append(f"{rf.path}: trop volumineux ({rf.size // 1024 // 1024} Mo)")
                    continue

                prev_etag = known.get(rf.path)
                if prev_etag and prev_etag == rf.etag:
                    result["skipped"] += 1
                    continue

                is_update = prev_etag is not None
                try:
                    content = await nextcloud.download(rf.path)
                    res = await ingest_file(
                        filename=Path(rf.path).name,
                        content=content,
                        tags=["nextcloud"],
                        source=_source_id(rf.path),
                        replace=is_update,
                    )
                    await state.upsert_file(rf.path, rf.etag, res["chunks_count"])
                    result["updated" if is_update else "added"] += 1
                except Exception as e:
                    logger.warning("Ingestion %s échouée : %s", rf.path, e)
                    result["errors"].append(f"{rf.path}: {e}")

            # Suppressions : fichiers connus mais plus présents côté Nextcloud
            for path in set(known) - seen_paths:
                try:
                    await delete_source(_source_id(path))
                    await state.remove_file(path)
                    result["removed"] += 1
                except Exception as e:
                    result["errors"].append(f"suppression {path}: {e}")

            logger.info(
                "Sync NC terminée : +%d ~%d -%d (skip %d, scan %d, %d erreurs)",
                result["added"], result["updated"], result["removed"],
                result["skipped"], result["scanned"], len(result["errors"]),
            )
        except Exception as e:
            logger.error("Sync NC erreur globale : %s", e)
            result = {"ok": False, "error": str(e)}
        finally:
            _running = False
            _last_result = result
        return result


async def periodic_loop() -> None:
    """Boucle de sync périodique — lancée au démarrage si activée."""
    interval = max(60, settings.nextcloud_sync_interval)
    logger.info("Sync Nextcloud périodique activée (toutes les %ds)", interval)
    # Petit délai initial pour laisser l'API démarrer
    await asyncio.sleep(10)
    while True:
        try:
            await sync()
        except Exception as e:
            logger.error("periodic_loop: %s", e)
        await asyncio.sleep(interval)
