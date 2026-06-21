"""Endpoints sauvegarde / restauration du « cerveau » de JARVIS."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response

from app.auth import require_api_key
from app.backup import export_all, import_all

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("", dependencies=[Depends(require_api_key)])
async def download_backup():
    """Télécharge une sauvegarde JSON (faits, tâches, webhooks)."""
    data = await export_all()
    body = json.dumps(data, ensure_ascii=False, indent=2)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M")
    return Response(
        content=body, media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="jarvis_backup_{stamp}.json"'})


@router.post("/restore", dependencies=[Depends(require_api_key)])
async def restore_backup(file: UploadFile = File(...), mode: str = "merge"):
    """Restaure depuis un fichier de sauvegarde. mode = merge | replace."""
    if mode not in ("merge", "replace"):
        raise HTTPException(400, "mode invalide (merge|replace)")
    raw = await file.read()
    try:
        data = json.loads(raw)
    except Exception:
        raise HTTPException(422, "Fichier JSON illisible")
    result = await import_all(data, mode=mode)
    if not result.get("ok"):
        raise HTTPException(422, result.get("error", "Échec de la restauration"))
    return result
