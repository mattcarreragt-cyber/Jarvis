"""Auth par API Key (header X-API-Key).

Usage solo, réseau LAN → une clé partagée est suffisante.
JWT sera ajouté si multi-utilisateur devient nécessaire.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(key: str | None = Security(_scheme)) -> str:
    if not settings.api_key:
        return "no-auth"  # auth désactivée (dev local sans clé configurée)
    if key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key invalide ou absente (header X-API-Key)",
        )
    return key
