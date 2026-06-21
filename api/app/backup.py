"""Sauvegarde / restauration des données durables de JARVIS.

Exporte le « cerveau » (faits mémorisés, tâches planifiées, webhooks) en un seul
JSON, et le réimporte. Permet de migrer de machine ou de se prémunir d'une perte.

Ne sauvegarde PAS les conversations (volumineuses, exportables séparément) ni les
médias (fichiers physiques sur le GPU). Dégradation gracieuse sans Postgres.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.db import get_pool

logger = logging.getLogger("jarvis.backup")

VERSION = 1

# table -> colonnes exportées (l'ordre compte pour l'insert)
_TABLES = {
    "memory_facts": ["id", "text", "kind", "session_id", "created_at"],
    "scheduled_tasks": ["id", "label", "kind", "payload", "schedule_kind",
                        "time_of_day", "interval_sec", "next_run", "enabled",
                        "last_run", "created_at"],
    "webhooks": ["id", "token", "label", "message", "enabled", "run_count",
                "last_triggered", "created_at"],
}
_DATETIME_COLS = {"created_at", "next_run", "last_run", "last_triggered"}


def _serialize(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _deserialize(col: str, value):
    if col in _DATETIME_COLS and isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return value


async def export_all() -> dict:
    """Exporte toutes les tables durables. {version, generated_at, tables:{...}}."""
    pool = await get_pool()
    out: dict = {"version": VERSION, "generated_at": datetime.utcnow().isoformat(),
                 "tables": {}}
    if pool is None:
        return out
    for table, cols in _TABLES.items():
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(f"SELECT {', '.join(cols)} FROM {table}")
            out["tables"][table] = [
                {c: _serialize(r[c]) for c in cols} for r in rows
            ]
        except Exception as e:
            logger.warning("export %s: %s", table, e)
            out["tables"][table] = []
    return out


async def import_all(data: dict, mode: str = "merge") -> dict:
    """Réimporte un backup.

    mode="merge" : ajoute sans écraser (ON CONFLICT id DO NOTHING).
    mode="replace" : vide chaque table puis réinsère.
    """
    pool = await get_pool()
    if pool is None:
        return {"ok": False, "error": "Base indisponible"}
    if not isinstance(data, dict) or "tables" not in data:
        return {"ok": False, "error": "Format de backup invalide"}

    stats: dict = {"ok": True, "mode": mode, "imported": {}}
    tables = data.get("tables", {})
    for table, cols in _TABLES.items():
        rows = tables.get(table, [])
        count = 0
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    if mode == "replace":
                        await conn.execute(f"DELETE FROM {table}")
                    for row in rows:
                        values = [_deserialize(c, row.get(c)) for c in cols]
                        placeholders = ", ".join(f"${i+1}" for i in range(len(cols)))
                        conflict = "" if mode == "replace" else \
                            f" ON CONFLICT (id) DO NOTHING"
                        await conn.execute(
                            f"INSERT INTO {table} ({', '.join(cols)}) "
                            f"VALUES ({placeholders}){conflict}", *values)
                        count += 1
            stats["imported"][table] = count
        except Exception as e:
            logger.warning("import %s: %s", table, e)
            stats["imported"][table] = f"erreur: {e}"
    return stats
