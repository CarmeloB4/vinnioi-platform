"""Persistenza Phase 3: una fonte non sovrascrive la dichiarazione di un'altra."""

import json
from datetime import datetime
from uuid import uuid4

from vinnioi.aica import document_id
from vinnioi.interventions import digest
from vinnioi.source_http import allowed_page
from vinnioi.store import _insert
from vinnioi.water_models import CalendarResult, WaterEvent


def initialize_integration(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS water_events(
            event_id VARCHAR PRIMARY KEY, source_id VARCHAR NOT NULL, title VARCHAR,
            categories JSON, declared_status VARCHAR, reliability VARCHAR,
            validation_status VARCHAR, first_seen_at TIMESTAMPTZ, last_seen_at TIMESTAMPTZ,
            payload JSON NOT NULL);
        CREATE TABLE IF NOT EXISTS event_observations(
            observation_id VARCHAR PRIMARY KEY, event_id VARCHAR NOT NULL,
            document_id VARCHAR NOT NULL, run_id VARCHAR NOT NULL,
            observed_at TIMESTAMPTZ NOT NULL, change_types JSON, payload JSON NOT NULL);
        CREATE TABLE IF NOT EXISTS event_municipalities(
            event_id VARCHAR, municipality_istat_code VARCHAR, relationship VARCHAR,
            evidence VARCHAR, PRIMARY KEY(event_id, municipality_istat_code));
        CREATE TABLE IF NOT EXISTS event_source_links(
            event_id VARCHAR, source_id VARCHAR, source_url VARCHAR, relationship VARCHAR,
            PRIMARY KEY(event_id, source_url));
        CREATE TABLE IF NOT EXISTS water_turnations(
            turnation_id VARCHAR PRIMARY KEY, source_url VARCHAR, municipality_istat_code VARCHAR,
            calendar_date DATE, validation_status VARCHAR, last_seen_at TIMESTAMPTZ,
            payload JSON NOT NULL);
        CREATE TABLE IF NOT EXISTS turnation_observations(
            observation_id VARCHAR PRIMARY KEY, turnation_id VARCHAR NOT NULL,
            run_id VARCHAR, document_id VARCHAR, observed_at TIMESTAMPTZ,
            present BOOLEAN, change_type VARCHAR, payload JSON NOT NULL);
        CREATE TABLE IF NOT EXISTS review_decisions(
            decision_id VARCHAR PRIMARY KEY, review_id VARCHAR NOT NULL,
            actor VARCHAR NOT NULL, decided_at TIMESTAMPTZ, action VARCHAR,
            expected_payload_hash VARCHAR, reason VARCHAR, evidence_url VARCHAR,
            rule_id VARCHAR, corrections JSON, before_payload JSON, after_payload JSON);
        CREATE TABLE IF NOT EXISTS event_correlations(
            candidate_id VARCHAR PRIMARY KEY, left_event_id VARCHAR, right_event_id VARCHAR,
            left_document_hash VARCHAR, right_document_hash VARCHAR,
            score DOUBLE, reasons JSON NOT NULL, status VARCHAR DEFAULT 'candidate');
        CREATE TABLE IF NOT EXISTS operator_coverage_evidence(
            evidence_id VARCHAR PRIMARY KEY, municipality_istat_code VARCHAR,
            claim_type VARCHAR, source_url VARCHAR, checked_on DATE, source_date DATE,
            document_hash VARCHAR, interpretation VARCHAR);
    """)
    connection.execute("""INSERT INTO sources VALUES ('siciliacque', 'Siciliacque',
        'https://www.siciliacque.it/avvisi/', false, false) ON CONFLICT DO NOTHING""")


def ingest_integration(
    store,
    *,
    events: list[WaterEvent],
    calendars: list[CalendarResult],
    observed_at: datetime,
    run_id: str | None = None,
    data_origin="real",
    input_errors: list[dict] | None = None,
    ignored_articles: int = 0,
) -> dict:
    connection = store.connection
    input_errors = input_errors or []
    if observed_at.tzinfo is None or data_origin not in {"real", "synthetic"}:
        raise ValueError("Timestamp e origine non validi")
    rows = [row for calendar in calendars for row in calendar.rows]
    if any(value.data_origin != data_origin for value in [*events, *rows]):
        raise ValueError("Origine incoerente nel batch")
    if any(
        o[0] != data_origin
        for o in connection.execute("SELECT DISTINCT data_origin FROM ingestion_runs").fetchall()
    ):
        raise ValueError("Non mescolare dati reali e sintetici")
    if any(value.acquired_at > observed_at for value in [*events, *calendars]):
        raise ValueError("Osservazione precedente all'acquisizione")
    if len({event.event_id for event in events}) != len(events):
        raise ValueError("Evento duplicato nello stesso batch")
    if len({str(c.source_url) for c in calendars}) != len(calendars):
        raise ValueError("Calendario duplicato nello stesso batch")
    run_id = run_id or str(uuid4())
    fingerprint = digest(
        [
            observed_at,
            data_origin,
            [event.model_dump(mode="json", exclude={"extracted_at"}) for event in events],
            [calendar.model_dump(mode="json") for calendar in calendars],
            input_errors,
            ignored_articles,
        ]
    )
    previous = connection.execute(
        "SELECT fingerprint, status FROM ingestion_runs WHERE run_id=?", [run_id]
    ).fetchone()
    if previous:
        if previous != (fingerprint, "completed"):
            raise ValueError("Replay incoerente o run non completato")
        return json.loads(
            connection.execute(
                "SELECT report FROM quality_reports WHERE run_id=?", [run_id]
            ).fetchone()[0]
        )
    last = connection.execute("""SELECT max(observed_at) FROM ingestion_runs
        WHERE status='completed'""").fetchone()[0]
    if last and observed_at <= last:
        raise ValueError("Run fuori ordine")
    _insert(
        connection,
        "ingestion_runs",
        dict(
            run_id=run_id,
            fingerprint=fingerprint,
            observed_at=observed_at,
            status="running",
            data_origin=data_origin,
        ),
    )
    try:
        connection.execute("BEGIN TRANSACTION")
        for event in events:
            _store_event(connection, event, run_id, observed_at)
        for calendar in calendars:
            _store_calendar(connection, calendar, run_id, observed_at)
        review_count = sum(e.validation_status == "needs_review" for e in events)
        review_count += sum(row.validation_status == "needs_review" for row in rows)
        report = dict(
            run_id=run_id,
            data_origin=data_origin,
            documents_analyzed=len(events) + len(calendars) + len(input_errors) + ignored_articles,
            ignored_articles=ignored_articles,
            input_errors=input_errors,
            water_events=len(events),
            turnation_cells=len(rows),
            review_records=review_count,
            errors=sum(len(c.errors) for c in calendars) + len(input_errors),
            coverage_istat_codes=sorted(
                {m.istat_code for e in events for m in e.municipalities}
                | {row.municipality_istat_code for row in rows if row.municipality_istat_code}
            ),
            publication_approved=False,
        )
        _insert(connection, "quality_reports", dict(run_id=run_id, report=report))
        connection.execute("UPDATE ingestion_runs SET status='completed' WHERE run_id=?", [run_id])
        connection.execute("COMMIT")
        return report
    except Exception as error:
        connection.execute("ROLLBACK")
        connection.execute(
            "UPDATE ingestion_runs SET status='failed', error=? WHERE run_id=?",
            [type(error).__name__, run_id],
        )
        raise


def _document(connection, source_id, url, sha, at, layout, complete=True):
    doc_id = document_id(url, sha)
    connection.execute(
        """INSERT INTO source_documents VALUES
        (?, ?, ?, ?, NULL, ?, NULL, '0.3.0', ?, ?) ON CONFLICT DO NOTHING""",
        [doc_id, source_id, url, sha, at, layout, complete],
    )
    return doc_id


def _store_event(connection, event, run_id, at):
    channel = "aica_communications" if event.source_id == "aica" else "siciliacque_notices"
    if not allowed_page(str(event.source_url), channel):
        raise ValueError("Provenienza evento fuori allowlist")
    if event.event_id != digest([event.source_id, str(event.source_url)]):
        raise ValueError("Identità evento incoerente con la fonte")
    if event.restoration_confirmed != ("ripristino_confermato" in event.categories):
        raise ValueError("Conferma di ripristino incoerente")
    doc_id = _document(
        connection,
        event.source_id,
        str(event.source_url),
        event.document_hash,
        event.acquired_at,
        "html_communication",
    )
    old = connection.execute(
        "SELECT first_seen_at, payload FROM water_events WHERE event_id=?", [event.event_id]
    ).fetchone()
    payload = event.model_dump(mode="json")
    comparable = {
        k: v
        for k, v in payload.items()
        if k not in {"acquired_at", "extracted_at", "document_hash"}
    }
    previous = json.loads(old[1]) if old else None
    change = (
        "new"
        if old is None
        else "known"
        if comparable
        == {
            k: v
            for k, v in previous.items()
            if k not in {"acquired_at", "extracted_at", "document_hash"}
        }
        else "changed"
    )
    # Anche un'osservazione dubbia resta visibile come tale; non è un fatto confermato.
    connection.execute("DELETE FROM water_events WHERE event_id=?", [event.event_id])
    _insert(
        connection,
        "water_events",
        dict(
            event_id=event.event_id,
            source_id=event.source_id,
            title=event.title,
            categories=event.categories,
            declared_status=event.declared_status,
            reliability=event.reliability,
            validation_status=event.validation_status,
            first_seen_at=old[0] if old else event.acquired_at,
            last_seen_at=at,
            payload=payload,
        ),
    )
    _insert(
        connection,
        "event_observations",
        dict(
            observation_id=digest([run_id, doc_id, event.event_id]),
            event_id=event.event_id,
            document_id=doc_id,
            run_id=run_id,
            observed_at=at,
            change_types=[change],
            payload=payload,
        ),
    )
    connection.execute("DELETE FROM event_municipalities WHERE event_id=?", [event.event_id])
    for mention in event.municipalities:
        _insert(
            connection,
            "event_municipalities",
            dict(
                event_id=event.event_id,
                municipality_istat_code=mention.istat_code,
                relationship=mention.relationship,
                evidence=mention.evidence,
            ),
        )
    connection.execute(
        "INSERT INTO event_source_links VALUES (?, ?, ?, 'source_report') ON CONFLICT DO NOTHING",
        [event.event_id, event.source_id, str(event.source_url)],
    )


def _store_calendar(connection, calendar, run_id, at):
    if not allowed_page(str(calendar.source_url), "aica_turnations"):
        raise ValueError("Provenienza calendario fuori allowlist")
    doc_id = _document(
        connection,
        "aica",
        str(calendar.source_url),
        calendar.version,
        calendar.acquired_at,
        "html_turnations",
        calendar.complete,
    )
    for row in calendar.rows:
        if row.calendar_version != calendar.version or row.source_url != calendar.source_url:
            raise ValueError("Provenienza calendario incoerente")
        old = connection.execute(
            "SELECT payload FROM water_turnations WHERE turnation_id=?", [row.turnation_id]
        ).fetchone()
        payload = row.model_dump(mode="json")

        def content(value):
            return {k: v for k, v in value.items() if k not in {"calendar_version", "acquired_at"}}

        change = (
            "new"
            if old is None
            else "known"
            if content(payload) == content(json.loads(old[0]))
            else "changed"
        )
        connection.execute("DELETE FROM water_turnations WHERE turnation_id=?", [row.turnation_id])
        _insert(
            connection,
            "water_turnations",
            dict(
                turnation_id=row.turnation_id,
                source_url=str(row.source_url),
                municipality_istat_code=row.municipality_istat_code,
                calendar_date=row.date,
                validation_status=row.validation_status,
                last_seen_at=at,
                payload=payload,
            ),
        )
        _insert(
            connection,
            "turnation_observations",
            dict(
                observation_id=digest([run_id, doc_id, row.turnation_id]),
                turnation_id=row.turnation_id,
                run_id=run_id,
                document_id=doc_id,
                observed_at=at,
                present=True,
                change_type=change,
                payload=payload,
            ),
        )
    # Non estrapoliamo cancellazioni/erogazione da calendari incompleti o senza date certe.
    if calendar.complete and all(row.validation_status == "validated" for row in calendar.rows):
        current = {row.turnation_id for row in calendar.rows}
        previous = connection.execute(
            """SELECT w.turnation_id FROM water_turnations w
            WHERE w.source_url=? AND EXISTS (SELECT 1 FROM turnation_observations o
            WHERE o.turnation_id=w.turnation_id AND o.present)""",
            [str(calendar.source_url)],
        ).fetchall()
        for (identifier,) in previous:
            if identifier in current:
                continue
            last = connection.execute(
                """SELECT present FROM turnation_observations
                WHERE turnation_id=? ORDER BY observed_at DESC LIMIT 1""",
                [identifier],
            ).fetchone()
            if last and last[0]:
                _insert(
                    connection,
                    "turnation_observations",
                    dict(
                        observation_id=digest([run_id, doc_id, identifier]),
                        turnation_id=identifier,
                        run_id=run_id,
                        document_id=doc_id,
                        observed_at=at,
                        present=False,
                        change_type="not_in_calendar",
                        payload={},
                    ),
                )
