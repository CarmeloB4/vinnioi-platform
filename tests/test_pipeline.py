"""Tutti i contenuti sono sintetici; nessun documento di terzi incluso."""

import hashlib
import json
from datetime import UTC, datetime

import duckdb
import httpx
import polars as pl
import pymupdf
import pytest
from pydantic import ValidationError
from vinnioi.aica import INDEX_URL, allowed_url, discover, document_id
from vinnioi.export import export_records
from vinnioi.models import Category, Record
from vinnioi.pdf import extract_pdf
from vinnioi.transport import Fetcher

URL = "https://www.aicaonline.it/interventi_programmati/interventi_test.pdf"


def record(**overrides):
    now = datetime.now(UTC)
    fields = dict(
        id=document_id(URL, "a" * 64),
        source_url=URL,
        discovered_at=now,
        fetched_at=now,
        comune="Comune sintetico",
        category=Category.PROGRAMMATO,
        content_sha256="a" * 64,
    )
    return Record(**(fields | overrides))


def test_discovery_filters_and_deduplicates():
    html = f'''<a href="{URL}">PDF Comune sintetico ↓</a>
    <a href="{URL}">PDF Comune sintetico ↓</a>
    <a href="https://example.org/x.pdf">Altro</a>
    <a href="/wp-content/uploads/bando.pdf">Bando</a>'''
    docs = discover(html)
    assert len(docs) == 1
    assert docs[0].comune == "Comune sintetico"
    with pytest.raises(ValueError):
        discover("<html>Markup cambiato</html>")


@pytest.mark.parametrize(
    "url",
    [
        "http://www.aicaonline.it/interventi-programmati/",
        "https://www.aicaonline.it.evil.test/interventi-programmati/",
        "https://www.aicaonline.it/interventi-programmati/?redirect=x",
    ],
)
def test_allowlist(url):
    assert not allowed_url(url)


def test_pdf_extract_and_empty_rejection():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 50), "TEST SINTETICO - intervento previsto, nessun ripristino")
        raw = doc.tobytes()
    parsed = extract_pdf(raw)
    assert "TEST SINTETICO" in parsed.pages[0]
    assert parsed.content_sha256 == hashlib.sha256(raw).hexdigest()
    with pymupdf.open() as doc:
        doc.new_page()
        blank = doc.tobytes()
    for bad in [blank, b"<html>errore</html>", b"%PDF-rotto"]:
        with pytest.raises((ValueError, pymupdf.FileDataError)):
            extract_pdf(bad)
    with pytest.raises(ValueError):
        extract_pdf(raw, max_pages=0)


def test_model_requires_evidence_and_timezone():
    with pytest.raises(ValidationError):
        record(category=Category.RIPRISTINO)
    with pytest.raises(ValidationError):
        record(fetched_at=datetime(2026, 1, 1))
    assert record().declared_status is None
    assert record(
        category=Category.RIPRISTINO,
        declared_status="ripristinato",
        evidence="Dichiarazione sintetica di ripristino",
    ).review_required


@pytest.mark.parametrize("empty", [False, True])
def test_exports_roundtrip(tmp_path, empty):
    records = [] if empty else [record()]
    export_records(records, tmp_path)
    assert len(json.loads((tmp_path / "records.json").read_text())) == len(records)
    assert pl.read_csv(tmp_path / "records.csv").height == len(records)
    assert pl.read_parquet(tmp_path / "records.parquet").height == len(records)
    with duckdb.connect(str(tmp_path / "vinnioi.duckdb")) as conn:
        assert conn.execute("select count(*) from records").fetchone()[0] == len(records)
    export_records(records, tmp_path)  # Rilancio idempotente del dataset corrente.


def test_transport_approval_and_robots():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /interventi_programmati/")
        return httpx.Response(200, text="index")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(PermissionError):
            Fetcher(client, approved=False)
        fetcher = Fetcher(client, approved=True)
        with pytest.raises(PermissionError):
            fetcher.fetch(URL)
        assert len(calls) == 1


@pytest.mark.parametrize(
    "body,status", [("<html>errore</html>", 200), ("", 404), ("", 429), ("", 302)]
)
def test_transport_fails_closed(body, status):
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(status, text=body))
    ) as client:
        with pytest.raises((PermissionError, httpx.HTTPStatusError)):
            Fetcher(client, approved=True).fetch(INDEX_URL)


def test_identity_changes_with_content():
    assert document_id(URL, "a" * 64) != document_id(URL, "b" * 64)


def test_cli_blocked_before_network(monkeypatch, tmp_path):
    from vinnioi.cli import main

    registry = tmp_path / "sources.toml"
    registry.write_text("[aica]\nacquisition_approved = false\n")
    monkeypatch.setattr("sys.argv", ["vinnioi", "--registry", str(registry)])
    monkeypatch.setattr(httpx, "Client", lambda: pytest.fail("Nessuna richiesta consentita"))
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
