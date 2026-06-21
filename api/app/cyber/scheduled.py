"""Audit cyber planifié + alerte sur baisse de score.

Appelé par le runner d'agenda pour les tâches de type "cyber". Compare le nouveau
score au précédent et signale toute régression dans la notification produite.
"""

from __future__ import annotations

import logging

from app.cyber import audit, store

logger = logging.getLogger("jarvis.cyber.scheduled")

_ALL = ("tous", "toutes", "all", "hôtes", "hotes", "machines", "serveurs")


async def _resolve_targets(target: str) -> list[dict]:
    hosts = await store.list_hosts()
    t = (target or "").lower()
    if not t or any(w in t for w in _ALL):
        return hosts
    for h in hosts:
        if h["label"].lower() in t:
            return [h]
    return []


async def run_and_alert(target: str) -> str:
    """Audit planifié d'un hôte (ou tous). Retourne un récap, avec alerte si baisse."""
    targets = await _resolve_targets(target)
    if not targets:
        return f"🛡️ Audit planifié : hôte « {target} » introuvable."

    lines = []
    for host in targets:
        # Score précédent (avant ce nouvel audit)
        hist = await store.score_history(host["id"], limit=1)
        prev = hist[-1]["score"] if hist else None

        res = await audit.run_audit(host)
        if not res.get("ok"):
            lines.append(f"❌ {host['label']} : audit impossible ({res.get('error')})")
            continue

        await store.save_findings(host["id"], res["findings"])
        score, grade = res["score"], res["grade"]
        await store.save_score(host["id"], score, grade)

        crit = res["summary"].get("critical", 0)
        high = res["summary"].get("high", 0)
        flags = []
        if prev is not None and score < prev:
            flags.append(f"⚠️ BAISSE {prev}→{score}")
        if crit:
            flags.append(f"🟥 {crit} critique(s)")
        if high:
            flags.append(f"🟧 {high} élevée(s)")
        suffix = ("  " + " · ".join(flags)) if flags else ""
        lines.append(f"🛡️ {host['label']} : {score}/100 ({grade}){suffix}")

    return "Audit cybersécurité planifié\n" + "\n".join(lines)
