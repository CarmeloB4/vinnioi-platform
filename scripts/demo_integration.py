"""Scenario Phase 3 sintetico: due fonti, calendario, revisione e backup/restore."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
from vinnioi.backup import LocalStorage, backup, restore
from vinnioi.correlations import record_candidates
from vinnioi.datasets import export_datasets
from vinnioi.events import parse_article
from vinnioi.frontend_data import frontend_preview
from vinnioi.integration_store import ingest_integration
from vinnioi.interventions import digest
from vinnioi.review import apply_review
from vinnioi.store import Store
from vinnioi.synthetic import synthetic_pdf, synthetic_row
from vinnioi.synthetic_water import article, calendar
from vinnioi.table_parser import parse_interventions
from vinnioi.turnations import parse_calendar
from vinnioi.water_models import ReviewDecision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/demo-integration"))
    args = parser.parse_args()
    database = args.output / "history.duckdb"
    if database.exists():
        parser.error("Usare una directory nuova; nessuno storico viene cancellato")
    store = Store(database)
    at = datetime(2026, 11, 20, 12, tzinfo=UTC)
    pdf_url = "https://www.aicaonline.it/interventi_programmati/interventi_agrigento.pdf"
    aica_url = "https://www.aicaonline.it/comunicazioni/fixture-sintetica/"
    sicilia_url = "https://www.siciliacque.it/avvisi/fixture-sintetica/"
    calendar_url = "https://www.aicaonline.it/turni-idrici-2/"
    try:
        technical = parse_interventions(
            synthetic_pdf(
                [
                    [
                        synthetic_row(address="VIA SINTETICA 99999"),
                        synthetic_row("2026_2", position="2", status="IGNOTO"),
                    ]
                ]
            ),
            source_url=pdf_url,
            municipality="Agrigento",
            observed_at=at - timedelta(seconds=1),
            extracted_at=at - timedelta(seconds=1),
            data_origin="synthetic",
        )
        store.ingest(
            [(pdf_url, "Agrigento", technical.rows[0].document_hash, technical)],
            observed_at=at - timedelta(seconds=1),
            data_origin="synthetic",
        )
        common = (
            "Si è verificato un guasto sull'acquedotto Gela-Aragona "
            "nel comune di Licata il 20/11/2026."
        )
        aica = parse_article(
            article("Guasto sintetico a Licata", [common]),
            source_id="aica",
            source_url=aica_url,
            acquired_at=at,
            data_origin="synthetic",
        )
        sicilia = parse_article(
            article("Guasto sintetico acquedotto Gela-Aragona", [common], source="siciliacque"),
            source_id="siciliacque",
            source_url=sicilia_url,
            acquired_at=at,
            data_origin="synthetic",
        )
        turn = parse_calendar(
            calendar(), source_url=calendar_url, acquired_at=at, data_origin="synthetic"
        )
        reports = [
            ingest_integration(
                store,
                events=[aica, sicilia],
                calendars=[turn],
                observed_at=at,
                run_id="synthetic-integration-1",
                data_origin="synthetic",
            )
        ]
        found = record_candidates(store)
        later = at + timedelta(days=1)
        restored = parse_article(
            article(
                "Ripristino sintetico a Licata",
                ["La fornitura idrica è stata ripristinata nel comune di Licata il 21/11/2026."],
            ),
            source_id="aica",
            source_url=aica_url,
            acquired_at=later,
            data_origin="synthetic",
        )
        updated = parse_calendar(
            calendar(value="10:00"),
            source_url=calendar_url,
            acquired_at=later,
            data_origin="synthetic",
        )
        reports.append(
            ingest_integration(
                store,
                events=[restored],
                calendars=[updated],
                observed_at=later,
                run_id="synthetic-integration-2",
                data_origin="synthetic",
            )
        )
        review_id, raw = store.connection.execute(
            "SELECT review_id, payload FROM review_records"
        ).fetchone()
        apply_review(
            store,
            ReviewDecision(
                decision_id="synthetic-review-1",
                review_id=review_id,
                expected_payload_hash=digest(json.loads(raw)),
                actor="revisore-sintetico",
                decided_at=later + timedelta(days=1),
                action="approve",
                evidence_url=pdf_url,
                reason="Correzione dello stato verificata esclusivamente nella fixture sintetica",
                corrections={"reported_status": "PIANIFICATO"},
            ),
        )
        preview = frontend_preview(store)
        (args.output / "frontend.synthetic.json").write_text(
            preview.model_dump_json(indent=2) + "\n"
        )
        snapshot = export_datasets(store, args.output / "exports")
        counts = {
            table: store.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in (
                "water_events",
                "event_observations",
                "water_turnations",
                "turnation_observations",
                "review_decisions",
                "event_correlations",
            )
        }
    finally:
        store.close()
    storage = LocalStorage(args.output / "backups")
    identifier = backup(database, snapshot, storage)
    destination = args.output / "restored"
    restore(identifier, destination, storage)
    with duckdb.connect(str(destination / "history.duckdb"), read_only=True) as connection:
        restored_counts = {
            table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in counts
        }
    if counts != restored_counts:
        raise RuntimeError("Ripristino non corrispondente")
    summary = dict(
        data_origin="synthetic",
        counts=counts,
        reports=reports,
        correlation_candidates=len(found),
        backup_restore_verified=True,
        publication_approved=False,
    )
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
