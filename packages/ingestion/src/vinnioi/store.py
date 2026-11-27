"""Storico locale DuckDB: transazione per run, osservazioni immutabili."""

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from vinnioi.aica import allowed_url, document_id
from vinnioi.interventions import Intervention, ParseResult, ValidationStatus, digest
from vinnioi.municipalities import municipalities, normalize
from vinnioi.quality import validate_rows

# Tipi espliciti, anche per export vuoti. Le date conservano timezone UTC.
INTERVENTION_COLUMNS = {
    name: (
        "TIMESTAMPTZ"
        if name.endswith("_at")
        else "INTEGER"
        if name in {"page_number", "row_number"}
        else "BOOLEAN"
        if name == "restoration_confirmed"
        else "JSON"
        if name == "issues"
        else "VARCHAR"
    )
    for name in Intervention.model_fields
}
FACT_FIELDS = (
    "municipality_istat_code",
    "address",
    "area",
    "intervention_type",
    "network_type",
    "published_at",
    "scheduled_at",
    "resolved_at",
    "restoration_confirmed",
)


def _insert(connection, table: str, values: dict):
    # table/keys sono costanti interne, mai input utente.
    keys = ", ".join(values)
    connection.execute(
        f"INSERT INTO {table} ({keys}) VALUES ({', '.join('?' for _ in values)})",
        [json.dumps(v) if isinstance(v, (list, dict)) else v for v in values.values()],
    )


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(str(path))
        self.connection.execute("SET TimeZone='UTC'")
        self._initialize()

    def close(self):
        self.connection.close()

    def _initialize(self):
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS municipalities(
                municipality_istat_code VARCHAR PRIMARY KEY, municipality VARCHAR NOT NULL,
                province VARCHAR NOT NULL, province_istat_code VARCHAR NOT NULL,
                operator_coverage VARCHAR NOT NULL);
            CREATE TABLE IF NOT EXISTS sources(
                source_id VARCHAR PRIMARY KEY, name VARCHAR, index_url VARCHAR,
                acquisition_approved BOOLEAN, redistribution_approved BOOLEAN);
            CREATE TABLE IF NOT EXISTS ingestion_runs(
                run_id VARCHAR PRIMARY KEY, fingerprint VARCHAR NOT NULL,
                observed_at TIMESTAMPTZ NOT NULL, status VARCHAR NOT NULL,
                data_origin VARCHAR NOT NULL, error VARCHAR);
            CREATE TABLE IF NOT EXISTS source_documents(
                document_id VARCHAR PRIMARY KEY, source_id VARCHAR NOT NULL,
                source_url VARCHAR NOT NULL, document_hash VARCHAR NOT NULL,
                municipality VARCHAR, first_observed_at TIMESTAMPTZ,
                document_generated_at VARCHAR, parser_version VARCHAR, layout VARCHAR,
                parse_complete BOOLEAN);
            CREATE TABLE IF NOT EXISTS intervention_observations(
                observation_id VARCHAR PRIMARY KEY, intervention_id VARCHAR NOT NULL,
                document_id VARCHAR NOT NULL, run_id VARCHAR NOT NULL,
                observed_at TIMESTAMPTZ NOT NULL, present BOOLEAN NOT NULL,
                change_types JSON NOT NULL, payload JSON NOT NULL);
            CREATE TABLE IF NOT EXISTS document_membership(
                source_url VARCHAR, intervention_id VARCHAR, present BOOLEAN NOT NULL,
                last_seen_at TIMESTAMPTZ NOT NULL, PRIMARY KEY(source_url, intervention_id));
            CREATE TABLE IF NOT EXISTS review_records(
                review_id VARCHAR PRIMARY KEY, run_id VARCHAR NOT NULL,
                document_id VARCHAR NOT NULL, payload JSON NOT NULL);
            CREATE TABLE IF NOT EXISTS quality_reports(
                run_id VARCHAR PRIMARY KEY, report JSON NOT NULL);
        """)
        version = self.connection.execute("SELECT version FROM schema_version").fetchall()
        if version and version not in ([(2,)], [(3,)]):
            raise ValueError("Versione database non supportata: migrazione necessaria")
        if not version:
            self.connection.execute("INSERT INTO schema_version VALUES (2)")
        columns = ", ".join(f"{k} {v}" for k, v in INTERVENTION_COLUMNS.items())
        self.connection.execute(
            f"CREATE TABLE IF NOT EXISTS interventions ({columns}, PRIMARY KEY(intervention_id))"
        )
        # Migrazione additiva transazionale; nessuna promozione dei vecchi record.
        self.connection.execute("BEGIN TRANSACTION")
        try:
            for name in ("address_original", "house_number", "address_quality", "area"):
                self.connection.execute(
                    f"ALTER TABLE interventions ADD COLUMN IF NOT EXISTS {name} VARCHAR"
                )
            from vinnioi.integration_store import initialize_integration

            initialize_integration(self.connection)
            self.connection.execute("UPDATE schema_version SET version=3")
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
        for row in municipalities():
            self.connection.execute(
                "INSERT INTO municipalities VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                list(row.values()),
            )
        self.connection.execute("""INSERT INTO sources VALUES
            ('aica', 'Azienda Idrica Comuni Agrigentini',
             'https://www.aicaonline.it/interventi-programmati/', false, false)
             ON CONFLICT DO NOTHING""")

    def record_input_failure(
        self,
        *,
        observed_at: datetime,
        error_type: str,
        run_id: str | None = None,
        data_origin: str = "real",
    ) -> dict:
        """Registra un'acquisizione fallita senza modificare eventi o presenze."""
        run_id = run_id or str(uuid4())
        origins = self.connection.execute(
            "SELECT DISTINCT data_origin FROM ingestion_runs"
        ).fetchall()
        if any(origin[0] != data_origin for origin in origins):
            raise ValueError("Non mescolare dati sintetici e reali nello stesso database")
        self.connection.execute("BEGIN TRANSACTION")
        try:
            _insert(
                self.connection,
                "ingestion_runs",
                dict(
                    run_id=run_id,
                    fingerprint=digest(["input_failure", observed_at, error_type]),
                    observed_at=observed_at,
                    status="failed",
                    data_origin=data_origin,
                    error=error_type,
                ),
            )
            report = self._report(run_id, [], data_origin)
            report["errors"] = 1
            report["document_errors"] = [f"input_failure:{error_type}"]
            _insert(self.connection, "quality_reports", dict(run_id=run_id, report=report))
            self.connection.execute("COMMIT")
            return report
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def records(self) -> list[dict]:
        cursor = self.connection.execute("SELECT * FROM interventions ORDER BY intervention_id")
        names = [col[0] for col in cursor.description]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]

    def ingest(
        self,
        documents: list[tuple[str, str, str, ParseResult]],
        *,
        observed_at: datetime,
        run_id: str | None = None,
        data_origin: str = "real",
    ) -> dict:
        """documents: (URL, comune richiesto, SHA256 originale, risultato parser)."""
        if observed_at.tzinfo is None or data_origin not in {"real", "synthetic"}:
            raise ValueError("Timezone e origine dati valide sono obbligatorie")
        if len({url for url, *_ in documents}) != len(documents):
            raise ValueError("URL duplicato nel run")
        # La persistenza rivalida i contratti anche se il chiamante non è la CLI.
        documents = [
            (url, name, sha, result.model_copy(deep=True)) for url, name, sha, result in documents
        ]
        by_identifier = {}
        for url, name, sha, result in documents:
            if not allowed_url(url) or not url.endswith(".pdf"):
                raise ValueError("URL documento non consentito")
            if not re.fullmatch(r"[a-f0-9]{64}", sha):
                raise ValueError("SHA256 documento non valido")
            if (
                result.expected_rows != len(result.rows)
                and "row_count_mismatch" not in result.errors
            ):
                result.errors.append("row_count_mismatch")
            if any(normalize(row.municipality or "") != normalize(name) for row in result.rows):
                result.errors.append("municipality_context_mismatch")
            if not result.complete and not result.errors:
                result.errors.append("incomplete_document")
            if result.errors or not result.complete:
                result.complete = False
                for row in result.rows:
                    row.issues = sorted(set(row.issues) | {"document_incomplete"})
            validate_rows(result.rows, observed_at)
            for row in result.rows:
                if row.intervention_id:
                    by_identifier.setdefault(row.intervention_id, []).append(row)
        # Documenti diversi nello stesso batch non possono imporre stati contraddittori.
        for rows in by_identifier.values():
            signatures = {
                digest([getattr(row, field) for field in (*FACT_FIELDS, "reported_status")])
                for row in rows
            }
            if len(signatures) > 1:
                for row in rows:
                    row.issues = sorted(set(row.issues) | {"conflicting_observations"})
                    row.validation_status = ValidationStatus.REVIEW
        fingerprint = digest(
            [
                observed_at.isoformat(),
                data_origin,
                [
                    (
                        url,
                        name,
                        sha,
                        result.model_dump(
                            mode="json", exclude={"rows": {"__all__": {"extracted_at"}}}
                        ),
                    )
                    for url, name, sha, result in documents
                ],
            ]
        )
        run_id = run_id or str(uuid4())
        previous = self.connection.execute(
            "SELECT fingerprint, status FROM ingestion_runs WHERE run_id=?", [run_id]
        ).fetchone()
        if previous:
            if previous != (fingerprint, "completed"):
                raise ValueError("run_id già usato con contenuto diverso o non completato")
            return json.loads(
                self.connection.execute(
                    "SELECT report FROM quality_reports WHERE run_id=?", [run_id]
                ).fetchone()[0]
            )
        origins = self.connection.execute(
            "SELECT DISTINCT data_origin FROM ingestion_runs"
        ).fetchall()
        if origins and any(origin[0] != data_origin for origin in origins):
            raise ValueError("Non mescolare dati sintetici e reali nello stesso database")
        _insert(
            self.connection,
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
            self.connection.execute("BEGIN TRANSACTION")
            for url, municipality, sha, result in documents:
                last = self.connection.execute(
                    """SELECT max(r.observed_at)
                    FROM source_documents d JOIN intervention_observations o USING(document_id)
                    JOIN ingestion_runs r USING(run_id) WHERE d.source_url=?""",
                    [url],
                ).fetchone()[0]
                # Anche documenti privi di righe sono protetti dai run in ordine temporale.
                latest_run = self.connection.execute("""SELECT max(observed_at) FROM ingestion_runs
                    WHERE status='completed'""").fetchone()[0]
                if (last and observed_at <= last) or (latest_run and observed_at <= latest_run):
                    raise ValueError("Run fuori ordine: usare un database separato per backfill")
                doc_id = document_id(url, sha)
                self.connection.execute(
                    """INSERT INTO source_documents VALUES
                    (?, 'aica', ?, ?, ?, ?, ?, '0.3.0', ?, ?) ON CONFLICT DO NOTHING""",
                    [
                        doc_id,
                        url,
                        sha,
                        municipality,
                        observed_at,
                        result.document_generated_at,
                        result.layout,
                        result.complete,
                    ],
                )
                validated = []
                for row in result.rows:
                    if row.document_hash != sha or str(row.source_url) != url:
                        raise ValueError("Provenienza incoerente tra documento e riga")
                    if row.data_origin != data_origin:
                        raise ValueError("Origine dati incoerente")
                    if row.validation_status == ValidationStatus.REVIEW:
                        _insert(
                            self.connection,
                            "review_records",
                            dict(
                                review_id=digest([run_id, doc_id, row.page_number, row.row_number]),
                                run_id=run_id,
                                document_id=doc_id,
                                payload=row.model_dump(mode="json"),
                            ),
                        )
                    else:
                        validated.append(row)
                        self._observe(row, run_id, doc_id, observed_at)
                # Qualsiasi quarantena/errore sopprime la riconciliazione delle assenze.
                if result.complete and all(
                    row.validation_status == ValidationStatus.VALIDATED for row in result.rows
                ):
                    current_ids = {row.intervention_id for row in validated}
                    missing = self.connection.execute(
                        """SELECT intervention_id
                        FROM document_membership WHERE source_url=? AND present""",
                        [url],
                    ).fetchall()
                    for (identifier,) in missing:
                        if identifier not in current_ids:
                            self._missing(identifier, url, run_id, doc_id, observed_at)
            report = self._report(run_id, documents, data_origin)
            _insert(self.connection, "quality_reports", dict(run_id=run_id, report=report))
            self.connection.execute(
                "UPDATE ingestion_runs SET status='completed' WHERE run_id=?", [run_id]
            )
            self.connection.execute("COMMIT")
            return report
        except Exception as error:
            self.connection.execute("ROLLBACK")
            self.connection.execute(
                "UPDATE ingestion_runs SET status='failed', error=? WHERE run_id=?",
                [type(error).__name__, run_id],
            )
            raise

    def _observe(self, row: Intervention, run_id: str, doc_id: str, observed_at: datetime):
        row = row.model_copy(deep=True)
        old_tuple = self.connection.execute(
            "SELECT * FROM interventions WHERE intervention_id=?", [row.intervention_id]
        ).fetchone()
        old_names = [col[0] for col in self.connection.description]
        old = dict(zip(old_names, old_tuple, strict=True)) if old_tuple else None
        changes = []
        if old:
            row.first_seen_at = old["first_seen_at"]
            if row.reported_status != old["reported_status"]:
                changes.append("status_changed")
            for field in FACT_FIELDS:
                old_value = old[field]
                new_value = getattr(row, field)
                if old_value != new_value:
                    changes.append("information_changed")
                    break
            was_present = self.connection.execute(
                """SELECT present FROM document_membership
                WHERE source_url=? AND intervention_id=?""",
                [str(row.source_url), row.intervention_id],
            ).fetchone()
            if was_present and not was_present[0]:
                changes.append("reappeared")
        else:
            changes.append("new")
        if row.restoration_confirmed and (not old or not old["restoration_confirmed"]):
            changes.append("restoration_confirmed")
        changes = sorted(set(changes)) or ["known"]
        row.last_seen_at = observed_at
        payload = row.model_dump(mode="json")
        # Sostituzione della proiezione corrente dentro la stessa transazione.
        self.connection.execute(
            "DELETE FROM interventions WHERE intervention_id=?", [row.intervention_id]
        )
        _insert(self.connection, "interventions", payload)
        self._observation(row.intervention_id, doc_id, run_id, observed_at, True, changes, payload)
        self.connection.execute(
            """INSERT INTO document_membership VALUES (?, ?, true, ?)
            ON CONFLICT(source_url, intervention_id) DO UPDATE SET present=true,
            last_seen_at=excluded.last_seen_at""",
            [str(row.source_url), row.intervention_id, observed_at],
        )

    def _missing(self, identifier, url, run_id, doc_id, observed_at):
        # Una mancata presenza non modifica stato, resolved_at né last_seen_at dell'intervento.
        self._observation(identifier, doc_id, run_id, observed_at, False, ["missing"], {})
        self.connection.execute(
            """UPDATE document_membership SET present=false
            WHERE source_url=? AND intervention_id=?""",
            [url, identifier],
        )

    def _observation(self, identifier, doc_id, run_id, at, present, changes, payload):
        _insert(
            self.connection,
            "intervention_observations",
            dict(
                observation_id=digest([run_id, doc_id, identifier]),
                intervention_id=identifier,
                document_id=doc_id,
                run_id=run_id,
                observed_at=at,
                present=present,
                change_types=changes,
                payload=payload,
            ),
        )

    def _report(self, run_id, documents, data_origin):
        rows = [row for *_, result in documents for row in result.rows]
        fields = list(Intervention.model_fields)
        valid = sum(row.validation_status == ValidationStatus.VALIDATED for row in rows)
        errors = [error for *_, result in documents for error in result.errors]
        issue_counts = {}
        for row in rows:
            for issue in row.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        covered = sorted(
            {row.municipality_istat_code for row in rows if row.municipality_istat_code}
        )
        changes = self.connection.execute(
            """SELECT change_types FROM intervention_observations
            WHERE run_id=?""",
            [run_id],
        ).fetchall()
        change_counts = {}
        for (value,) in changes:
            for change in json.loads(value):
                change_counts[change] = change_counts.get(change, 0) + 1
        address_counts = {}
        for row in rows:
            address_counts[row.address_quality] = address_counts.get(row.address_quality, 0) + 1
        return dict(
            address_quality_counts=address_counts,
            run_id=run_id,
            data_origin=data_origin,
            documents_analyzed=len(documents),
            interventions_extracted=len(rows),
            validated_records=valid,
            review_records=len(rows) - valid,
            errors=len(errors),
            document_errors=errors,
            issue_counts=issue_counts,
            coverage_istat_codes=covered,
            administrative_municipalities=43,
            covered_municipalities=len(covered),
            administrative_coverage_percent=round(len(covered) / 43 * 100, 2),
            field_completeness_percent={
                field: round(
                    sum(getattr(row, field) is not None for row in rows) / len(rows) * 100, 2
                )
                if rows
                else None
                for field in fields
            },
            change_counts=change_counts,
        )
