"""Snapshot locali di export. Nessuna pubblicazione e nessun documento incluso."""

import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

from vinnioi.store import Store

QUERIES = {
    **{
        table: f"SELECT * FROM {table}"
        for table in (
            "water_events",
            "event_observations",
            "event_municipalities",
            "water_turnations",
            "turnation_observations",
            "event_source_links",
            "review_decisions",
            "event_correlations",
            "operator_coverage_evidence",
        )
    },
    "interventions": "SELECT * FROM interventions ORDER BY intervention_id",
    "intervention_history": """SELECT o.observation_id, o.intervention_id, o.document_id,
        o.run_id, o.observed_at, o.present, o.change_types, d.source_url, d.document_hash,
        o.payload FROM intervention_observations o JOIN source_documents d USING(document_id)
        ORDER BY o.observed_at, o.observation_id""",
    "municipalities": "SELECT * FROM municipalities ORDER BY municipality_istat_code",
    "municipality_summary": """SELECT m.municipality_istat_code, m.municipality, m.province,
        m.operator_coverage,
        (SELECT count(*) FROM source_documents d
         WHERE lower(d.municipality)=lower(m.municipality)) AS observed_document_versions,
        count(i.intervention_id) AS known_interventions,
        count(i.intervention_id) FILTER (WHERE i.restoration_confirmed) AS confirmed_restorations,
        max(i.last_seen_at) AS last_seen_at FROM municipalities m
        LEFT JOIN interventions i USING(municipality_istat_code)
        GROUP BY m.municipality_istat_code, m.municipality, m.province, m.operator_coverage
        ORDER BY m.municipality_istat_code""",
    "data_quality_report": """SELECT r.run_id, r.observed_at, r.status, r.data_origin, q.report
        FROM ingestion_runs r LEFT JOIN quality_reports q USING(run_id)
        ORDER BY r.observed_at, r.run_id""",
    "review_records": """SELECT * FROM review_records ORDER BY run_id, review_id""",
    "sources": "SELECT * FROM sources ORDER BY source_id",
    "source_documents": "SELECT * FROM source_documents ORDER BY document_id",
    "ingestion_runs": "SELECT * FROM ingestion_runs ORDER BY observed_at, run_id",
}


def export_datasets(store: Store, root: Path) -> Path:
    """Directory immutabile; LATEST aggiornato atomicamente solo a export completato."""
    root.mkdir(parents=True, exist_ok=True)
    name = str(uuid4())
    temporary = root / f".tmp-{name}"
    snapshot = root / name
    temporary.mkdir()
    connection = store.connection
    try:
        connection.execute("BEGIN TRANSACTION")
        for dataset, query in QUERIES.items():
            for extension, options in {
                "csv": "FORMAT CSV, HEADER TRUE, NULL '\\N'",
                "json": "FORMAT JSON, ARRAY TRUE",
                "parquet": "FORMAT PARQUET, COMPRESSION ZSTD",
            }.items():
                # Filename passato come parametro; le query sono costanti interne.
                connection.execute(
                    f"COPY ({query}) TO ? ({options})", [str(temporary / f"{dataset}.{extension}")]
                )
        counts = {
            name: connection.execute(f"SELECT count(*) FROM ({query})").fetchone()[0]
            for name, query in QUERIES.items()
        }
        (temporary / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 3,
                    "datasets": counts,
                    "publication_approved": False,
                    "csv_null": "\\N",
                    "municipalities_attribution": "ISTAT, CC BY 4.0; elaborazione Vinnioi",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        connection.execute("COMMIT")
        temporary.rename(snapshot)
        pointer = root / f".LATEST-{name}"
        pointer.write_text(name + "\n")
        os.replace(pointer, root / "LATEST")
        return snapshot
    except Exception:
        # ROLLBACK può arrivare dopo un COMMIT se fallisce il filesystem.
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        shutil.rmtree(temporary, ignore_errors=True)
        raise
