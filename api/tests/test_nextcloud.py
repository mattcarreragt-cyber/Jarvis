"""Tests Nextcloud — extraction, sync incrémentale, agent (mocks, sans serveur NC)."""

import io
from unittest.mock import AsyncMock, patch

from app.agents.nextcloud_agent import NextcloudAgent
from app.contracts import AgentRequest, AgentStatus
from app.docs.extract import extract_text, is_supported, kind_for
from app.sources import sync
from app.sources.nextcloud import RemoteFile, _parse_propfind


# ─── Extraction ──────────────────────────────────────────────────────────────

def test_is_supported():
    assert is_supported("a.pdf")
    assert is_supported("b.docx")
    assert is_supported("c.xlsx")
    assert is_supported("d.pptx")
    assert is_supported("e.png")
    assert not is_supported("f.zip")


def test_kind_for():
    assert kind_for("x.png") == "image"
    assert kind_for("x.xlsx") == "xlsx"
    assert kind_for("x.pptx") == "pptx"
    assert kind_for("x.txt") == "doc"


def test_extract_txt():
    assert "bonjour" in extract_text("a.txt", b"bonjour le monde")


def test_extract_image_context():
    # Sans tesseract : au moins le nom + dossier indexés
    txt = extract_text("/Photos/ma_super_image.png", b"\x89PNG\r\n")
    assert "ma super image" in txt
    assert "Photos" in txt


def test_extract_legacy_rejected():
    import pytest
    with pytest.raises(ValueError, match="legacy"):
        extract_text("vieux.doc", b"\xd0\xcf")


def test_extract_docx_roundtrip():
    import docx
    d = docx.Document()
    d.add_paragraph("Xenum performance moteur")
    buf = io.BytesIO()
    d.save(buf)
    txt = extract_text("test.docx", buf.getvalue())
    assert "Xenum performance moteur" in txt


# ─── PROPFIND parsing ────────────────────────────────────────────────────────

_PROPFIND_XML = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/remote.php/dav/files/matt/Documents/</d:href>
    <d:propstat><d:prop>
      <d:resourcetype><d:collection/></d:resourcetype>
      <d:getetag>"abc"</d:getetag>
    </d:prop></d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/files/matt/Documents/fiche.pdf</d:href>
    <d:propstat><d:prop>
      <d:resourcetype/>
      <d:getetag>"etag123"</d:getetag>
      <d:getcontentlength>2048</d:getcontentlength>
      <d:getcontenttype>application/pdf</d:getcontenttype>
    </d:prop></d:propstat>
  </d:response>
</d:multistatus>"""


def test_parse_propfind():
    files = _parse_propfind(_PROPFIND_XML, "/remote.php/dav/files/matt")
    by_path = {f.path: f for f in files}
    assert "/Documents/fiche.pdf" in by_path
    pdf = by_path["/Documents/fiche.pdf"]
    assert pdf.is_dir is False
    assert pdf.etag == "etag123"
    assert pdf.size == 2048
    assert by_path["/Documents"].is_dir is True


# ─── Sync incrémentale ───────────────────────────────────────────────────────

def _rf(path, etag, size=100):
    return RemoteFile(path=path, etag=etag, size=size, last_modified="",
                      content_type="", is_dir=False)


async def test_sync_added_and_skipped():
    remote = [_rf("/a.txt", "e1"), _rf("/b.pdf", "e2"), _rf("/c.zip", "e3")]
    with patch("app.sources.sync.nextcloud._configured", return_value=True), \
         patch("app.sources.sync.nextcloud.walk_files", new=AsyncMock(return_value=remote)), \
         patch("app.sources.sync.state.known_etags", new=AsyncMock(return_value={"/a.txt": "e1"})), \
         patch("app.sources.sync.nextcloud.download", new=AsyncMock(return_value=b"data")), \
         patch("app.sources.sync.ingest_file", new=AsyncMock(return_value={"chunks_count": 3})), \
         patch("app.sources.sync.state.upsert_file", new=AsyncMock()), \
         patch("app.sources.sync.delete_source", new=AsyncMock()), \
         patch("app.sources.sync.state.remove_file", new=AsyncMock()):
        result = await sync.sync()
    assert result["ok"] is True
    assert result["added"] == 1      # b.pdf (a.txt skip, c.zip non supporté)
    assert result["skipped"] == 1    # a.txt etag identique


async def test_sync_updated_and_removed():
    remote = [_rf("/a.txt", "e1-new")]   # a modifié ; b absent → supprimé
    with patch("app.sources.sync.nextcloud._configured", return_value=True), \
         patch("app.sources.sync.nextcloud.walk_files", new=AsyncMock(return_value=remote)), \
         patch("app.sources.sync.state.known_etags",
               new=AsyncMock(return_value={"/a.txt": "e1-old", "/b.pdf": "e2"})), \
         patch("app.sources.sync.nextcloud.download", new=AsyncMock(return_value=b"data")), \
         patch("app.sources.sync.ingest_file", new=AsyncMock(return_value={"chunks_count": 2})) as ing, \
         patch("app.sources.sync.state.upsert_file", new=AsyncMock()), \
         patch("app.sources.sync.delete_source", new=AsyncMock()) as dele, \
         patch("app.sources.sync.state.remove_file", new=AsyncMock()):
        result = await sync.sync()
    assert result["updated"] == 1
    assert result["removed"] == 1
    # update doit appeler ingest avec replace=True
    assert ing.call_args.kwargs["replace"] is True
    dele.assert_awaited()   # suppression du fichier disparu


async def test_sync_not_configured():
    with patch("app.sources.sync.nextcloud._configured", return_value=False):
        result = await sync.sync()
    assert result["ok"] is False


# ─── Agent ───────────────────────────────────────────────────────────────────

async def test_nextcloud_agent_no_results():
    with patch("app.agents.nextcloud_agent.search", new=AsyncMock(return_value=([], "keyword"))):
        resp = await NextcloudAgent().handle(AgentRequest(
            request_id="n1", session_id="s1", intent="nextcloud",
            message="mes fichiers sur le cloud",
        ))
    assert resp.status == AgentStatus.ok
    assert "Aucun fichier" in resp.content


async def test_nextcloud_agent_with_results_keyword():
    hits = [{"text": "Contrat Xenum 2026", "source": "nextcloud:/Documents/contrat.pdf",
             "score": 2, "tags": ["nextcloud"]}]
    with patch("app.agents.nextcloud_agent.search", new=AsyncMock(return_value=(hits, "keyword"))), \
         patch("app.agents.rag_reply.synthesize", new=AsyncMock(return_value=None)):
        resp = await NextcloudAgent().handle(AgentRequest(
            request_id="n2", session_id="s1", intent="nextcloud",
            message="contrat xenum",
        ))
    assert "/Documents/contrat.pdf" in resp.content
    assert "nextcloud:" not in resp.content   # le préfixe est nettoyé à l'affichage


async def test_nextcloud_agent_llm_synthesis():
    hits = [{"text": "Contrat Xenum 2026", "source": "nextcloud:/Documents/contrat.pdf",
             "score": 0.9, "tags": ["nextcloud"]}]
    with patch("app.agents.nextcloud_agent.search", new=AsyncMock(return_value=(hits, "semantic"))), \
         patch("app.agents.rag_reply.synthesize",
               new=AsyncMock(return_value="Le contrat court jusqu'en 2026 [1].")):
        resp = await NextcloudAgent().handle(AgentRequest(
            request_id="n3", session_id="s1", intent="nextcloud",
            message="jusqu'à quand court le contrat ?",
        ))
    assert "2026" in resp.content
    assert "Sources" in resp.content
