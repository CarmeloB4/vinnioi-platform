"""Integrazione e regressioni delle tre fonti usando solo fixture sintetiche."""

import json
from datetime import UTC, datetime, timedelta

import duckdb
import httpx
import pytest
from vinnioi.backup import LocalStorage, backup, restore
from vinnioi.correlations import candidates, record_candidates
from vinnioi.datasets import export_datasets
from vinnioi.events import discover_articles, parse_article
from vinnioi.frontend_data import frontend_preview
from vinnioi.integration_store import ingest_integration
from vinnioi.interventions import digest
from vinnioi.review import apply_review
from vinnioi.source_http import PageFetcher, allowed_page
from vinnioi.store import Store
from vinnioi.synthetic import synthetic_pdf, synthetic_row
from vinnioi.synthetic_water import article, calendar
from vinnioi.table_parser import parse_interventions
from vinnioi.turnations import parse_calendar
from vinnioi.water_models import ReviewDecision

AT = datetime(2026, 11, 20, 12, tzinfo=UTC)
AICA = "https://www.aicaonline.it/comunicazioni/test-sintetico/"
SICILIA = "https://www.siciliacque.it/avvisi/test-sintetico/"
TURNS = "https://www.aicaonline.it/turni-idrici-2/"
PDF = "https://www.aicaonline.it/interventi_programmati/interventi_agrigento.pdf"


def event(
    text="Un guasto alla rete idrica interessa il comune di Licata.", *, source="aica", at=AT
):
    return parse_article(
        article("Avviso sintetico", [text], source=source),
        source_id=source,
        source_url=AICA if source == "aica" else SICILIA,
        acquired_at=at,
        data_origin="synthetic",
    )


def turns(*, at=AT, **kwargs):
    return parse_calendar(
        calendar(**kwargs), source_url=TURNS, acquired_at=at, data_origin="synthetic"
    )


@pytest.fixture
def store(tmp_path):
    value = Store(tmp_path / "history.duckdb")
    yield value
    value.close()


@pytest.mark.parametrize(
    "text,category",
    [
        ("Un guasto alla rete interessa il comune di Licata.", "guasto"),
        ("Interruzione della fornitura idrica nel comune di Licata.", "interruzione"),
        ("Manutenzione programmata nel comune di Licata domani.", "manutenzione_programmata"),
        ("Riduzione della portata nel comune di Licata.", "riduzione_portata"),
        ("Emergenza idrica nel comune di Licata.", "emergenza_idrica"),
        ("Divieto di uso dell'acqua nel comune di Licata.", "potabilita"),
        ("La fornitura idrica è stata ripristinata nel comune di Licata.", "ripristino_confermato"),
    ],
)
def test_categories(text, category):
    value = event(text)
    assert category in value.categories
    assert value.municipalities[0].istat_code == "084021"
    assert value.municipalities[0].relationship == "explicit_service_area"


@pytest.mark.parametrize(
    "text",
    [
        "Non si sono verificati guasti nel comune di Licata.",
        "Nessuna interruzione della fornitura nel comune di Licata.",
        "Smentita la crisi idrica nel comune di Licata.",
        "Lo sportello di Licata sarà aperto domani.",
    ],
)
def test_negative_and_editorial_not_events(text):
    assert event(text) is None


@pytest.mark.parametrize(
    "text",
    [
        "Il ripristino della fornitura nel comune di Licata è previsto domani.",
        "La fornitura sarà ripristinata domani nel comune di Licata.",
        "Un guasto nel comune di Licata; si prevede di ripristinare la fornitura entro domani.",
    ],
)
def test_future_restoration_is_never_confirmation(text):
    value = event(text)
    assert value is None or not value.restoration_confirmed


def test_real_date_precision_and_relative_dates():
    value = event(
        "Oggi si sono verificati disservizi nel comune di Licata, ma domani tornerà regolare."
    )
    times = {item.text: item for item in value.temporal_references}
    assert times["oggi"].kind == "actual"
    assert times["oggi"].date.isoformat() == "2026-11-20"
    assert times["domani"].kind == "planned"
    assert times["domani"].date.isoformat() == "2026-11-21"
    assert value.published_at.utcoffset().total_seconds() == 3600
    assert not value.restoration_confirmed


def test_no_date_anchor_is_not_download_date():
    value = parse_article(
        article(
            "Guasto sintetico",
            ["Guasto nel comune di Licata, ripristino previsto domani."],
            published="ignota",
        ),
        source_id="aica",
        source_url=AICA,
        acquired_at=AT,
        data_origin="synthetic",
    )
    assert value.published_at is None and value.published_on is None
    assert value.temporal_references[0].date is None
    assert value.validation_status == "needs_review"


def test_pipeline_names_do_not_assign_all_municipalities():
    value = event(
        "Guasto sull'acquedotto Gela-Aragona con fornitura sospesa nel comune di Licata.",
        source="siciliacque",
    )
    assert value.network_level == "adduction"
    assert {m.name for m in value.municipalities} == {"Licata"}
    assert value.pipelines == ["Gela-Aragona"]
    assert event("Guasto sull'acquedotto Gela-Aragona.", source="siciliacque") is None


def test_province_name_is_not_city_impact():
    value = event("Guasto in provincia di Agrigento con fornitura sospesa nel comune di Licata.")
    assert {m.name for m in value.municipalities} == {"Licata"}


def test_html_discovery_scoped_and_deduplicated():
    html = f'<a href="{AICA}">test</a><a href="{AICA}">test</a><a href="https://evil.test/">x</a>'
    assert discover_articles(
        html, index_url="https://www.aicaonline.it/comunicazioni/", channel="aica_communications"
    ) == [AICA]
    with pytest.raises(ValueError):
        discover_articles("", index_url=AICA, channel="aica_communications")


def test_calendar_dates_notes_blank_and_provenance():
    value = turns()
    assert value.complete and len(value.rows) == 2
    assert value.rows[0].date.isoformat() == "2026-11-20"
    assert value.rows[0].time_slot == "08:00"
    assert value.rows[1].notes == "Rinviato"
    assert all(not row.actual_delivery_confirmed for row in value.rows)
    blank = turns(value="").rows[0]
    assert blank.time_slot is None and blank.value_original is None


def test_calendar_partial_labels_do_not_invent_year_or_month():
    value = turns(full_dates=False)
    assert all(row.date is None for row in value.rows)
    assert all(row.validation_status == "needs_review" for row in value.rows)
    assert all("calendar_date_incomplete" in row.issues for row in value.rows)


def test_calendar_unknown_and_duplicate_slots_are_preserved_for_review():
    value = turns(value="ORARIO SCONOSCIUTO", municipality="UTENZE TEST", duplicate=True)
    assert not value.complete and len(value.rows) == 4
    assert len({row.turnation_id for row in value.rows}) == 4
    assert all(row.validation_status == "needs_review" for row in value.rows)
    assert "duplicate_calendar_slot" in value.errors


def test_calendar_agrigento_district_is_explicit_not_inferred():
    value = turns(municipality="AGRIGENTO – VILLASETA")
    assert value.rows[0].municipality_istat_code == "084001"
    assert value.rows[0].district == "VILLASETA"


def test_event_and_calendar_history_are_independent(store):
    first = ingest_integration(
        store,
        events=[event()],
        calendars=[turns()],
        observed_at=AT,
        data_origin="synthetic",
        run_id="one",
    )
    assert first["water_events"] == 1 and first["turnation_cells"] == 2
    assert (
        ingest_integration(
            store,
            events=[event()],
            calendars=[turns()],
            observed_at=AT,
            data_origin="synthetic",
            run_id="one",
        )
        == first
    )
    later = AT + timedelta(days=1)
    ingest_integration(
        store,
        events=[event("La fornitura è stata ripristinata nel comune di Licata.", at=later)],
        calendars=[turns(at=later, value="10:00")],
        observed_at=later,
        data_origin="synthetic",
    )
    assert store.connection.execute("SELECT count(*) FROM water_events").fetchone()[0] == 1
    assert store.connection.execute("SELECT count(*) FROM event_observations").fetchone()[0] == 2
    assert (
        store.connection.execute(
            "SELECT count(*) FROM turnation_observations WHERE change_type='changed'"
        ).fetchone()[0]
        == 1
    )
    assert len(store.records()) == 0


def test_correlations_remain_candidates_with_reasons(store):
    text = "Guasto sull'acquedotto Gela-Aragona nel comune di Licata il 20/11/2026."
    left, right = event(text), event(text, source="siciliacque")
    found = candidates([left, right])
    assert len(found) == 1 and found[0]["status"] == "candidate"
    assert found[0]["reasons"]["municipality_mentions"] == ["084021"]
    ingest_integration(
        store, events=[left, right], calendars=[], observed_at=AT, data_origin="synthetic"
    )
    record_candidates(store)
    record_candidates(store)
    assert store.connection.execute("SELECT count(*) FROM event_correlations").fetchone()[0] == 1
    assert store.connection.execute("SELECT count(*) FROM water_events").fetchone()[0] == 2
    assert not candidates([left, left])


def test_99999_is_address_quality_not_invalid_intervention():
    result = parse_interventions(
        synthetic_pdf([[synthetic_row(address="VIA SINTETICA 99999")]]),
        source_url=PDF,
        municipality="Agrigento",
        observed_at=AT,
        data_origin="synthetic",
    )
    row = result.rows[0]
    assert row.validation_status == "validated"
    assert row.address_original == "VIA SINTETICA 99999"
    assert row.address == "VIA SINTETICA"
    assert row.house_number is None and row.address_quality == "house_number_unavailable"


def quarantine(store):
    result = parse_interventions(
        synthetic_pdf([[synthetic_row(status="IGNOTO")]]),
        source_url=PDF,
        municipality="Agrigento",
        observed_at=AT,
        data_origin="synthetic",
    )
    store.ingest(
        [(PDF, "Agrigento", result.rows[0].document_hash, result)],
        observed_at=AT,
        data_origin="synthetic",
    )
    identifier, payload = store.connection.execute(
        "SELECT review_id, payload FROM review_records"
    ).fetchone()
    before = json.loads(payload)
    decision = ReviewDecision(
        decision_id="review-1",
        review_id=identifier,
        expected_payload_hash=digest(before),
        actor="revisore-test",
        decided_at=datetime.now(UTC),
        action="approve",
        reason="Correzione sintetica verificata nella fonte di test",
        evidence_url=PDF,
        corrections={"reported_status": "PIANIFICATO"},
    )
    return decision


def test_explicit_review_is_audited_without_deleting_quarantine(store):
    decision = quarantine(store)
    result = apply_review(store, decision)
    assert result["intervention_id"]
    assert len(store.records()) == 1
    assert store.connection.execute("SELECT count(*) FROM review_records").fetchone()[0] == 1
    assert store.connection.execute("SELECT count(*) FROM review_decisions").fetchone()[0] == 1
    with pytest.raises(ValueError):
        apply_review(store, decision)


def test_review_rejects_stale_hash_and_provenance_patch(store):
    decision = quarantine(store)
    with pytest.raises(ValueError, match="Hash"):
        apply_review(store, decision.model_copy(update={"expected_payload_hash": "b" * 64}))
    with pytest.raises(ValueError, match="provenienza"):
        apply_review(store, decision.model_copy(update={"corrections": {"source_id": "x"}}))
    assert not store.records()


def test_rejection_is_audited_without_promoting_record(store):
    decision = quarantine(store).model_copy(update={"action": "reject"})
    apply_review(store, decision)
    assert not store.records()
    assert store.connection.execute("SELECT action FROM review_decisions").fetchone()[0] == "reject"


def test_frontend_contract_minimizes_and_does_not_claim_service(store):
    ingest_integration(
        store, events=[event()], calendars=[turns()], observed_at=AT, data_origin="synthetic"
    )
    value = frontend_preview(store)
    assert not value.publication_approved
    assert len(value.territorial_indicators) == 43
    assert all(row["service_status"] == "unknown" for row in value.territorial_indicators)
    assert value.events_by_municipality["084021"]
    assert "evidence" not in value.recent_events[0]
    assert "street_description" not in value.turnations[0]


def test_backup_restore_integrity_and_no_overwrite(tmp_path):
    database = tmp_path / "history.duckdb"
    store = Store(database)
    ingest_integration(
        store, events=[event()], calendars=[turns()], observed_at=AT, data_origin="synthetic"
    )
    snapshot = export_datasets(store, tmp_path / "exports")
    store.close()
    storage = LocalStorage(tmp_path / "backups")
    identifier = backup(database, snapshot, storage)
    destination = tmp_path / "restored"
    restore(identifier, destination, storage)
    with duckdb.connect(str(destination / "history.duckdb"), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM event_observations").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM turnation_observations").fetchone()[0] == 2
    with pytest.raises(FileExistsError):
        restore(identifier, destination, storage)
    (storage.root / identifier / "history.duckdb").write_bytes(b"corrotto")
    with pytest.raises(ValueError, match="Integrità"):
        restore(identifier, tmp_path / "bad-restore", storage)
    assert not (tmp_path / "bad-restore").exists()


def test_backup_rejects_active_writer_and_paths(store, tmp_path):
    storage = LocalStorage(tmp_path / "backups")
    with pytest.raises((ValueError, duckdb.Error)):
        backup(tmp_path / "history.duckdb", tmp_path / "missing", storage)
    with pytest.raises(ValueError):
        storage.put("../escape", b"bad")


@pytest.mark.parametrize(
    "channel,url",
    [
        ("aica_communications", "https://www.aicaonline.it/comunicazioni/test/?redirect=1"),
        ("siciliacque_notices", "https://www.siciliacque.it/wp-admin/"),
        ("aica_turnations", "https://evil.test/turni-idrici-2/"),
    ],
)
def test_page_allowlists(channel, url):
    assert not allowed_page(url, channel)


def test_real_acquisition_is_blocked_before_http():
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("Nessuna rete"))
    ) as client:
        with pytest.raises(PermissionError):
            PageFetcher(client, channel="siciliacque_notices", approved=False)


@pytest.mark.parametrize(
    "text",
    ["Acqua non potabile nel comune di Licata.", "L'acqua non è potabile nel comune di Licata."],
)
def test_potability_warning_is_not_a_negated_event(text):
    assert "potabilita" in event(text).categories


def test_calendar_duplicate_quarantine_can_be_persisted(store):
    value = turns(duplicate=True)
    report = ingest_integration(
        store, events=[], calendars=[value], observed_at=AT, data_origin="synthetic"
    )
    assert report["errors"] == 2
    assert report["review_records"] == 4
    assert (
        store.connection.execute("SELECT count(*) FROM turnation_observations").fetchone()[0] == 4
    )


def test_input_errors_and_ignored_documents_are_persisted(store):
    errors = [{"source_url": AICA, "error": "layout_not_recognized"}]
    report = ingest_integration(
        store,
        events=[],
        calendars=[],
        observed_at=AT,
        data_origin="synthetic",
        input_errors=errors,
        ignored_articles=1,
    )
    assert report["documents_analyzed"] == 2 and report["errors"] == 1
    saved = json.loads(store.connection.execute("SELECT report FROM quality_reports").fetchone()[0])
    assert saved["input_errors"] == errors


def test_backup_rejects_stale_snapshot_even_when_row_counts_match(tmp_path):
    database = tmp_path / "history.duckdb"
    store = Store(database)
    ingest_integration(
        store, events=[event()], calendars=[], observed_at=AT, data_origin="synthetic"
    )
    snapshot = export_datasets(store, tmp_path / "exports")
    later = AT + timedelta(days=1)
    ingest_integration(
        store,
        events=[event("La fornitura è stata ripristinata nel comune di Licata.", at=later)],
        calendars=[],
        observed_at=later,
        data_origin="synthetic",
    )
    store.close()
    with pytest.raises(ValueError, match="Snapshot"):
        backup(database, snapshot, LocalStorage(tmp_path / "backups"))


def test_verified_extra_urban_title_is_scoped_to_correct_url():
    content = synthetic_pdf([[synthetic_row()]], municipality="LICATA EXTRA URBANA")
    url = "https://www.aicaonline.it/interventi_programmati/interventi_licata_extra_urbana.pdf"
    value = parse_interventions(
        content, source_url=url, municipality="Licata", observed_at=AT, data_origin="synthetic"
    )
    assert value.complete and value.rows[0].area == "extra urbana"
    mismatch = parse_interventions(
        content, source_url=PDF, municipality="Agrigento", observed_at=AT, data_origin="synthetic"
    )
    assert not mismatch.complete


def test_phase2_migration_preserves_quarantine_and_does_not_promote(tmp_path):
    database = tmp_path / "phase2.duckdb"
    # Database minimale con la stessa struttura di quarantena Phase 2.
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE TABLE schema_version(version INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO schema_version VALUES (2)")
        connection.execute(
            "CREATE TABLE review_records(review_id VARCHAR PRIMARY KEY, run_id VARCHAR, "
            "document_id VARCHAR, payload JSON)"
        )
        connection.execute(
            "INSERT INTO review_records VALUES ('legacy', 'old-run', 'old-doc', ?)",
            [json.dumps({"issues": ["address_placeholder"], "address": "VIA TEST 99999"})],
        )
    store = Store(database)
    try:
        assert store.connection.execute("SELECT version FROM schema_version").fetchone()[0] == 3
        assert not store.records()
        old = json.loads(
            store.connection.execute("SELECT payload FROM review_records").fetchone()[0]
        )
        assert old["issues"] == ["address_placeholder"]
        assert store.connection.execute("SELECT count(*) FROM review_decisions").fetchone()[0] == 0
    finally:
        store.close()


def test_integration_cli_local_manifest_and_preview(tmp_path):
    import subprocess
    import sys

    (tmp_path / "article.html").write_bytes(
        article(
            "Guasto sintetico", ["Si è verificato un guasto nel comune di Licata il 20/11/2026."]
        )
    )
    (tmp_path / "calendar.html").write_bytes(calendar())
    manifest = tmp_path / "inputs.json"
    manifest.write_text(
        json.dumps(
            [
                {"channel": "aica_communications", "path": "article.html", "source_url": AICA},
                {"channel": "aica_turnations", "path": "calendar.html", "source_url": TURNS},
            ]
        )
    )
    database = tmp_path / "cli.duckdb"
    command = [sys.executable, "-c", "from vinnioi.integration_cli import main; main()"]
    result = subprocess.run(
        command
        + [
            "ingest",
            "--manifest",
            str(manifest),
            "--synthetic",
            "--observed-at",
            AT.isoformat(),
            "--database",
            str(database),
            "--output",
            str(tmp_path / "export"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        command
        + ["preview", "--database", str(database), "--output", str(tmp_path / "preview.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "preview.json").read_text())["data_origin"] == "synthetic"


def test_integration_cli_all_real_channels_blocked(monkeypatch, tmp_path):
    from vinnioi.integration_cli import main

    monkeypatch.setattr(
        httpx, "Client", lambda: pytest.fail("Nessuna rete prima dell'approvazione")
    )
    for channel in ["aica_communications", "siciliacque_notices", "aica_turnations"]:
        monkeypatch.setattr(
            "sys.argv",
            [
                "vinnioi-integrate",
                "ingest",
                "--channel",
                channel,
                "--database",
                str(tmp_path / "blocked.duckdb"),
                "--output",
                str(tmp_path / "out"),
            ],
        )
        with pytest.raises(SystemExit) as error:
            main()
        assert error.value.code == 2
    assert not (tmp_path / "blocked.duckdb").exists()


def test_page_fetcher_respects_robots_for_new_source(monkeypatch):
    calls = []
    monkeypatch.setattr("vinnioi.transport.time.sleep", lambda _: None)

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, text="User-agent: *\nDisallow: /avvisi/")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client, channel="siciliacque_notices", approved=True)
        with pytest.raises(PermissionError):
            fetcher.fetch(SICILIA)
    assert calls == ["/robots.txt"]


def test_coverage_evidence_does_not_certify_service(store):
    from vinnioi.coverage import coverage_evidence, record_coverage

    index = f'<a href="{PDF}">PDF Agrigento ↓</a>'.encode()
    evidence = coverage_evidence(
        intervention_index=index, calendar=calendar(), checked_on=AT.date()
    )
    record_coverage(store, evidence)
    record_coverage(store, evidence)
    assert (
        store.connection.execute("SELECT count(*) FROM operator_coverage_evidence").fetchone()[0]
        == 2
    )
    assert store.connection.execute(
        "SELECT DISTINCT operator_coverage FROM municipalities"
    ).fetchall() == [("unknown",)]


def test_restore_rejects_manifest_path_traversal(tmp_path):
    storage = LocalStorage(tmp_path / "storage")
    identifier = "00000000-0000-0000-0000-000000000000"
    storage.put(
        identifier + "/manifest.json",
        json.dumps(
            {"backup_version": 1, "files": {"../escape": {}, "history.duckdb": {}}}
        ).encode(),
    )
    with pytest.raises(ValueError, match="Percorso"):
        restore(identifier, tmp_path / "destination", storage)
    assert not (tmp_path / "escape").exists()


def test_integration_rolls_back_invalid_source_reference(store):
    from pydantic import HttpUrl

    invalid = event()
    invalid.source_url = HttpUrl("https://evil.test/")
    with pytest.raises(ValueError, match="Provenienza"):
        ingest_integration(
            store, events=[invalid], calendars=[], observed_at=AT, data_origin="synthetic"
        )
    assert store.connection.execute("SELECT count(*) FROM water_events").fetchone()[0] == 0
    assert store.connection.execute("SELECT status FROM ingestion_runs").fetchone()[0] == "failed"


def test_frontend_failed_update_does_not_replace_last_source_observation(store):
    ingest_integration(
        store, events=[event()], calendars=[], observed_at=AT, data_origin="synthetic"
    )
    later = AT + timedelta(days=1)
    store.record_input_failure(observed_at=later, error_type="ReadTimeout", data_origin="synthetic")
    value = frontend_preview(store)
    assert value.last_update["status"] == "failed"
    assert value.last_update["last_source_observed_at"] == AT
    assert value.last_update["last_attempt_at"] == later
