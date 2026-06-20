"""Connecteur Nextcloud via WebDAV — lecture seule, 100% local.

Auth : app password (Nextcloud → Paramètres → Sécurité → Mots de passe d'application).
On ne touche JAMAIS en écriture au Nextcloud de l'utilisateur.

WebDAV : on liste récursivement avec PROPFIND Depth:1 (Depth:infinity est souvent
désactivé côté serveur), puis on télécharge chaque fichier avec GET.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import unquote, urljoin
from xml.etree import ElementTree as ET

import httpx

from app.config import settings

logger = logging.getLogger("jarvis.nextcloud")

_DAV_NS = "{DAV:}"


@dataclass
class RemoteFile:
    path: str            # chemin relatif à la racine WebDAV de l'utilisateur, ex. "/Documents/x.pdf"
    etag: str            # change quand le contenu change → sync incrémentale
    size: int
    last_modified: str
    content_type: str
    is_dir: bool


def _configured() -> bool:
    return bool(settings.nextcloud_url and settings.nextcloud_user and settings.nextcloud_password)


def _dav_base() -> str:
    base = settings.nextcloud_url.rstrip("/")
    return f"{base}/remote.php/dav/files/{settings.nextcloud_user}"


def _auth() -> tuple[str, str]:
    return (settings.nextcloud_user, settings.nextcloud_password)


def _parse_propfind(xml_text: str, dav_prefix: str) -> list[RemoteFile]:
    files: list[RemoteFile] = []
    root = ET.fromstring(xml_text)
    for resp in root.findall(f"{_DAV_NS}response"):
        href_el = resp.find(f"{_DAV_NS}href")
        if href_el is None or not href_el.text:
            continue
        href = unquote(href_el.text)
        # Chemin relatif à la racine de l'utilisateur
        rel = href.split(dav_prefix, 1)[-1] if dav_prefix in href else href
        rel = "/" + rel.strip("/")

        propstat = resp.find(f"{_DAV_NS}propstat")
        prop = propstat.find(f"{_DAV_NS}prop") if propstat is not None else None
        if prop is None:
            continue

        resourcetype = prop.find(f"{_DAV_NS}resourcetype")
        is_dir = resourcetype is not None and resourcetype.find(f"{_DAV_NS}collection") is not None

        def _txt(tag: str) -> str:
            el = prop.find(f"{_DAV_NS}{tag}")
            return (el.text or "").strip().strip('"') if el is not None and el.text else ""

        files.append(RemoteFile(
            path=rel,
            etag=_txt("getetag"),
            size=int(_txt("getcontentlength") or 0),
            last_modified=_txt("getlastmodified"),
            content_type=_txt("getcontenttype"),
            is_dir=is_dir,
        ))
    return files


_PROPFIND_BODY = (
    '<?xml version="1.0"?>'
    '<d:propfind xmlns:d="DAV:"><d:prop>'
    '<d:getetag/><d:getcontentlength/><d:getlastmodified/>'
    '<d:getcontenttype/><d:resourcetype/>'
    '</d:prop></d:propfind>'
)


async def _list_dir(client: httpx.AsyncClient, path: str) -> list[RemoteFile]:
    url = _dav_base() + path
    r = await client.request(
        "PROPFIND", url,
        headers={"Depth": "1", "Content-Type": "application/xml"},
        content=_PROPFIND_BODY,
        auth=_auth(),
    )
    r.raise_for_status()
    dav_prefix = f"/remote.php/dav/files/{settings.nextcloud_user}"
    entries = _parse_propfind(r.text, dav_prefix)
    # PROPFIND Depth:1 inclut le dossier lui-même → on l'exclut
    norm = path.rstrip("/") or "/"
    return [e for e in entries if (e.path.rstrip("/") or "/") != norm]


async def walk_files() -> list[RemoteFile]:
    """Parcourt récursivement Nextcloud depuis NEXTCLOUD_ROOT, retourne les fichiers."""
    if not _configured():
        raise RuntimeError("Nextcloud non configuré (NEXTCLOUD_URL/USER/PASSWORD)")

    out: list[RemoteFile] = []
    async with httpx.AsyncClient(timeout=30) as client:
        stack = [settings.nextcloud_root or "/"]
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            try:
                entries = await _list_dir(client, current)
            except Exception as e:
                logger.warning("PROPFIND %s échoué : %s", current, e)
                continue
            for e in entries:
                if e.is_dir:
                    stack.append(e.path)
                else:
                    out.append(e)
    logger.info("Nextcloud : %d fichiers découverts", len(out))
    return out


async def download(path: str) -> bytes:
    """Télécharge le contenu d'un fichier Nextcloud."""
    url = _dav_base() + path
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(url, auth=_auth())
        r.raise_for_status()
        return r.content


async def ping() -> bool:
    """Vérifie que Nextcloud est joignable et l'auth valide."""
    if not _configured():
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.request(
                "PROPFIND", _dav_base() + "/",
                headers={"Depth": "0"}, auth=_auth(),
            )
            return r.status_code < 400
    except Exception:
        return False
