"""Regressioni offline con PDF generati esplicitamente sintetici."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import duckdb
import pytest
from pydantic import HttpUrl
from vinnioi.datasets import export_datasets
from vinnioi.interventions import ValidationStatus
from vinnioi.municipalities import lookup, municipalities
from vinnioi.quality import validate_rows
from vinnioi.store import Store
from vinnioi.synthetic import synthetic_pdf, synthetic_row
from vinnioi.table_parser import parse_interventions

URL = "https://www.aicaonline.it/interventi_programmati/interventi_agrigento.pdf"
AT = datetime(2026, 1, 1, 12, tzinfo=UTC)


def parsed(rows=None, *, at=AT, municipality="Agrigento", **kwargs):
    pdf = synthetic_pdf(
        [rows if rows is not None else [synthetic_row()]], municipality=municipality, **kwargs
    )
    return parse_interventions(
        pdf,
        source_url=URL,
        municipality=municipality,
        observed_at=at,
        extracted_at=at,
        data_origin="synthetic",
    )


def ingest(store, result, *, at=AT, run_id=None, url=URL):
    sha = result.rows[0].document_hash if result.rows else hashlib.sha256(b"empty").hexdigest()
    return store.ingest(
        [(url, "Agrigento", sha, result)], observed_at=at, run_id=run_id, data_origin="synthetic"
    )


@pytest.fixture
def store(tmp_path):
    store = Store(tmp_path / "history.duckdb")
    yield store
    store.close()


def test_istat_reference_and_normalization():
    data = municipalities()
    assert len(data) == len({row["municipality_istat_code"] for row in data}) == 43
    assert lookup("CANICATTI")["municipality_istat_code"] == "084011"
    assert lookup("Sant’Angelo Muxaro")["municipality_istat_code"] == "084039"
    assert lookup("Atlantide") is None
    assert {row["operator_coverage"] for row in data} == {"unknown"}


def test_geometry_parser_preserves_ids_and_newlines():
    row = synthetic_row(address="VIA TEST\nSINTETICA 10")
    result = parsed([row])
    assert result.complete
    assert result.rows[0].source_intervention_id == "2026_1"
    assert result.rows[0].address == "VIA TEST SINTETICA 10"
    assert result.rows[0].network_type == "IDRICA"
    assert result.rows[0].validation_status == ValidationStatus.VALIDATED
    assert result.rows[0].published_at is None
    assert result.rows[0].scheduled_at is None
    assert result.rows[0].resolved_at is None
    assert result.document_generated_at == "01/01/2026 alle 10:00:00"


def test_cross_page_network_continuation():
    row = synthetic_row()
    row[3] = "Idrico leggero"
    pdf = synthetic_pdf(
        [[row], [["", "", "", "IDRICA", "", ""], synthetic_row("2026_2", position="2")]]
    )
    result = parse_interventions(pdf, source_url=URL, municipality="Agrigento", observed_at=AT)
    assert result.complete and len(result.rows) == 2
    assert all(row.network_type == "IDRICA" for row in result.rows)


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"total": 3}, "row_count_mismatch"),
        ({"title": False}, "municipality_title_mismatch"),
        (
            {"header": ["Nuovo", "layout", "non", "riconosciuto", "dal", "parser"]},
            "page_1:unsupported_table",
        ),
    ],
)
def test_parser_layout_changes_fail_closed(kwargs, error):
    result = parsed(**kwargs)
    assert not result.complete
    assert error in result.errors
    assert all(row.validation_status == ValidationStatus.REVIEW for row in result.rows)


@pytest.mark.parametrize("content", [b"<html>404</html>", b"%PDF-invalid"])
def test_invalid_pdf_is_reported(content):
    result = parse_interventions(content, source_url=URL, municipality="Agrigento", observed_at=AT)
    assert not result.complete and result.errors


def test_duplicate_missing_unknown_incomplete_quality():
    rows = [
        synthetic_row(),
        synthetic_row(position="2"),
        synthetic_row("", position="3"),
        synthetic_row("2026_4", position="4", status="SCONOSCIUTO", address=""),
    ]
    result = parsed(rows, municipality="Comune non riconosciuto")
    assert len(result.rows) == 4
    assert all(row.validation_status == ValidationStatus.REVIEW for row in result.rows)
    assert "missing_source_identifier" in result.rows[2].issues
    assert "unknown_status" in result.rows[3].issues
    assert "unknown_municipality" in result.rows[0].issues
    duplicate = parsed([synthetic_row(), synthetic_row(position="2")])
    assert all("duplicate_identifier" in row.issues for row in duplicate.rows)


def test_dates_and_provenance_checks():
    row = parsed().rows[0]
    row.published_at = AT + timedelta(days=1)
    row.resolved_at = AT
    row.scheduled_at = AT + timedelta(days=1)
    row.source_id = "fonte_inventata"
    validate_rows([row], AT)
    assert {
        "publication_in_future",
        "inconsistent_dates",
        "invalid_provenance",
        "resolution_without_confirmation",
    } <= set(row.issues)


def test_incremental_known_changed_missing_and_reappeared(store):
    first = parsed([synthetic_row(), synthetic_row("2026_2", position="2")])
    report = ingest(store, first, run_id="first")
    assert report["change_counts"] == {"new": 2}
    assert ingest(store, first, run_id="first") == report  # Retry identico.
    at2 = AT + timedelta(days=1)
    known = parsed([synthetic_row(), synthetic_row("2026_2", position="2")], at=at2)
    report = ingest(store, known, at=at2, run_id="known")
    assert report["change_counts"] == {"known": 2}
    assert store.connection.execute("select count(*) from source_documents").fetchone()[0] == 1
    at3 = at2 + timedelta(days=1)
    changed = parsed([synthetic_row(status="COMPLETATO", address="VIA TEST SINTETICA 2")], at=at3)
    report = ingest(store, changed, at=at3)
    assert report["change_counts"] == {"status_changed": 1, "information_changed": 1, "missing": 1}
    assert all(row["resolved_at"] is None for row in store.records())
    assert all(not row["restoration_confirmed"] for row in store.records())
    at4 = at3 + timedelta(days=1)
    report = ingest(store, parsed(at=at4), at=at4)
    # Un intervento rimasto assente non genera assenze ripetute.
    assert "missing" not in report["change_counts"]
    at5 = at4 + timedelta(days=1)
    report = ingest(store, parsed([synthetic_row("2026_2")], at=at5), at=at5)
    assert report["change_counts"]["reappeared"] == 1
    values = {row["source_intervention_id"]: row for row in store.records()}
    assert values["2026_2"]["first_seen_at"] == AT
    assert values["2026_2"]["last_seen_at"] == at5


def test_explicit_restoration_without_invented_time(store):
    row = parsed([synthetic_row(status="FORNITURA RIPRISTINATA")])
    report = ingest(store, row)
    assert report["change_counts"]["restoration_confirmed"] == 1
    assert store.records()[0]["resolved_at"] is None
    assert store.records()[0]["restoration_confirmed"]


def test_partial_or_review_document_never_proves_absence(store):
    ingest(store, parsed())
    at = AT + timedelta(days=1)
    incomplete = parsed([], at=at, total=1)
    report = ingest(store, incomplete, at=at)
    assert "missing" not in report["change_counts"]
    at += timedelta(days=1)
    review = parsed([synthetic_row("2026_2", status="STATO NUOVO")], at=at)
    report = ingest(store, review, at=at)
    assert report["review_records"] == 1
    assert "missing" not in report["change_counts"]
    assert len(store.records()) == 1
    assert store.connection.execute("select count(*) from review_records").fetchone()[0] == 1


def test_empty_complete_snapshot_marks_missing_without_resolution(store):
    ingest(store, parsed())
    at = AT + timedelta(days=1)
    report = ingest(store, parsed([], at=at, total=0), at=at)
    assert report["change_counts"] == {"missing": 1}
    assert store.records()[0]["last_seen_at"] == AT
    assert store.records()[0]["resolved_at"] is None


def test_reject_reused_run_identifier_and_backfill(store):
    ingest(store, parsed(), run_id="one")
    with pytest.raises(ValueError, match="run_id"):
        ingest(store, parsed([synthetic_row(status="COMPLETATO")]), run_id="one")
    with pytest.raises(ValueError, match="fuori ordine"):
        ingest(store, parsed(), run_id="backfill")
    assert (
        store.connection.execute(
            "select status from ingestion_runs where run_id='backfill'"
        ).fetchone()[0]
        == "failed"
    )
    assert (
        store.connection.execute("select count(*) from intervention_observations").fetchone()[0]
        == 1
    )


def test_transaction_rolls_back_corrupt_provenance(store):
    result = parsed()
    result.rows[0].document_hash = "b" * 64
    with pytest.raises(ValueError, match="Provenienza"):
        store.ingest(
            [(URL, "Agrigento", "a" * 64, result)], observed_at=AT, data_origin="synthetic"
        )
    assert not store.records()
    assert store.connection.execute("select count(*) from source_documents").fetchone()[0] == 0


@pytest.mark.parametrize("empty", [False, True])
def test_exports_types_nulls_and_history_roundtrip(store, tmp_path, empty):
    if not empty:
        ingest(store, parsed())
    snapshot = export_datasets(store, tmp_path / "export")
    assert (snapshot.parent / "LATEST").read_text().strip() == snapshot.name
    manifest = json.loads((snapshot / "manifest.json").read_text())
    assert not manifest["publication_approved"]
    assert manifest["datasets"]["municipalities"] == 43
    records = json.loads((snapshot / "interventions.json").read_text())
    assert len(records) == (0 if empty else 1)
    if records:
        assert records[0]["resolved_at"] is None
    with duckdb.connect() as connection:
        assert (
            connection.execute(
                "select count(*) from read_parquet(?)", [str(snapshot / "municipalities.parquet")]
            ).fetchone()[0]
            == 43
        )
        # VARCHAR mantiene gli zeri iniziali dei codici.
        assert (
            connection.execute(
                "select municipality_istat_code from read_parquet(?) limit 1",
                [str(snapshot / "municipalities.parquet")],
            ).fetchone()[0]
            == "084001"
        )


def test_real_synthetic_separation(store):
    ingest(store, parsed())
    with pytest.raises(ValueError, match="mescolare"):
        store.ingest([], observed_at=AT + timedelta(days=1), data_origin="real")


def test_conflicting_documents_are_quarantined(store):
    from vinnioi.interventions import ParseResult

    result = parsed()
    other_url = "https://www.aicaonline.it/interventi_programmati/interventi_agrigento_extra.pdf"
    other = parsed([synthetic_row(status="COMPLETATO")])
    for row in other.rows:
        row.source_url = HttpUrl(other_url)
    other = ParseResult.model_validate(other.model_dump())
    report = store.ingest(
        [
            (URL, "Agrigento", result.rows[0].document_hash, result),
            (other_url, "Agrigento", other.rows[0].document_hash, other),
        ],
        observed_at=AT,
        data_origin="synthetic",
    )
    assert report["review_records"] == 2
    assert report["issue_counts"]["conflicting_observations"] == 2
    assert not store.records()


def test_persistence_revalidates_forged_validated_row(store):
    result = parsed()
    result.rows[0].source_intervention_id = None
    result.rows[0].validation_status = ValidationStatus.VALIDATED
    report = ingest(store, result)
    assert report["review_records"] == 1
    assert not store.records()


def test_history_cli_local_manifest_and_quality_exit(tmp_path):
    import subprocess
    import sys

    (tmp_path / "synthetic.pdf").write_bytes(synthetic_pdf([[synthetic_row()]]))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps([{"source_url": URL, "municipality": "Agrigento", "path": "synthetic.pdf"}])
    )
    database = tmp_path / "cli.duckdb"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from vinnioi.history_cli import main; main()",
            "--manifest",
            str(manifest),
            "--synthetic",
            "--observed-at",
            AT.isoformat(),
            "--database",
            str(database),
            "--output",
            str(tmp_path / "exports"),
            "--run-id",
            "cli",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '"validated_records": 1' in result.stdout
    assert database.exists()
    (tmp_path / "synthetic.pdf").write_bytes(synthetic_pdf([[synthetic_row(status="IGNOTO")]]))
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from vinnioi.history_cli import main; main()",
            "--manifest",
            str(manifest),
            "--synthetic",
            "--observed-at",
            (AT + timedelta(days=1)).isoformat(),
            "--database",
            str(database),
            "--output",
            str(tmp_path / "exports"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert '"review_records": 1' in result.stdout
    with duckdb.connect(str(database)) as connection:
        assert connection.execute("select count(*) from ingestion_runs").fetchone()[0] == 2


def test_history_cli_real_sources_remain_blocked(monkeypatch):
    from vinnioi.history_cli import main

    monkeypatch.setattr("sys.argv", ["vinnioi-history"])
    monkeypatch.setattr("httpx.Client", lambda: pytest.fail("Acquisizione non autorizzata"))
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


def test_input_failure_keeps_existing_history_and_reports_error(store):
    ingest(store, parsed())
    report = store.record_input_failure(
        observed_at=AT + timedelta(days=1), error_type="HTTPStatusError", data_origin="synthetic"
    )
    assert report["errors"] == 1
    assert report["documents_analyzed"] == 0
    assert all(value is None for value in report["field_completeness_percent"].values())
    assert len(store.records()) == 1
    assert store.connection.execute("select present from document_membership").fetchone()[0]


def test_replay_keeps_real_extraction_time_without_duplicate_run(store):
    content = synthetic_pdf([[synthetic_row()]])
    first = parse_interventions(
        content, source_url=URL, municipality="Agrigento", observed_at=AT, data_origin="synthetic"
    )
    assert first.rows[0].extracted_at > AT  # Estrazione attuale, osservazione precedente.
    report = ingest(store, first, run_id="replay-times")
    later = parse_interventions(
        content,
        source_url=URL,
        municipality="Agrigento",
        observed_at=AT,
        data_origin="synthetic",
        extracted_at=first.rows[0].extracted_at + timedelta(seconds=1),
    )
    assert ingest(store, later, run_id="replay-times") == report
    assert (
        store.connection.execute("select count(*) from intervention_observations").fetchone()[0]
        == 1
    )
