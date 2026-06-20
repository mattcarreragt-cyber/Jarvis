"""Store en mémoire pour les actions en attente de confirmation.

Clé = request_id (str UUID), valeur = ConfirmationRequest.
TTL implicite : nettoyage au démarrage uniquement (les pending expirent avec la session).
"""

from __future__ import annotations

from app.contracts import ConfirmationRequest

_store: dict[str, ConfirmationRequest] = {}


def save(req: ConfirmationRequest) -> None:
    _store[req.request_id] = req


def pop(request_id: str) -> ConfirmationRequest | None:
    return _store.pop(request_id, None)


def exists(request_id: str) -> bool:
    return request_id in _store
