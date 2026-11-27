"""Revisione esplicita e append-only della quarantena degli interventi."""

import json

from vinnioi.interventions import Intervention, digest
from vinnioi.quality import validate_rows
from vinnioi.store import _insert
from vinnioi.water_models import ReviewDecision

RECOMPUTABLE = {
    "unknown_municipality",
    "municipality_code_mismatch",
    "missing_source_identifier",
    "invalid_source_identifier",
    "unknown_status",
    "unknown_network",
    "incomplete_record",
    "address_placeholder",
    "publication_in_future",
    "inconsistent_dates",
    "resolution_without_confirmation",
}
CORRECTABLE = {
    "source_intervention_id",
    "municipality",
    "address",
    "intervention_type",
    "network_type",
    "reported_status",
}


def apply_review(store, decision: ReviewDecision) -> dict:
    connection = store.connection
    existing = connection.execute(
        "SELECT review_id FROM review_decisions WHERE decision_id=?", [decision.decision_id]
    ).fetchone()
    if existing:
        raise ValueError("decision_id già registrato: le decisioni sono immutabili")
    target = connection.execute(
        "SELECT payload, document_id, run_id FROM review_records WHERE review_id=?",
        [decision.review_id],
    ).fetchone()
    if target is None:
        raise ValueError("Record in quarantena non trovato")
    before = json.loads(target[0])
    if digest(before) != decision.expected_payload_hash:
        raise ValueError("Hash del record non corrispondente: revisione obsoleta")
    if connection.execute(
        "SELECT 1 FROM review_decisions WHERE review_id=?", [decision.review_id]
    ).fetchone():
        raise ValueError("Record già revisionato; creare una nuova osservazione per nuove evidenze")
    if str(decision.evidence_url) != before["source_url"]:
        raise ValueError("La revisione deve riferire il documento originale verificato")
    if not set(decision.corrections) <= CORRECTABLE:
        raise ValueError("Correzione di provenienza o campo non consentito")
    original = Intervention.model_validate(before)
    if decision.decided_at < original.extracted_at:
        raise ValueError("Decisione precedente all'estrazione")
    after = None
    row = None
    if decision.action == "approve":
        values = before | decision.corrections
        values["issues"] = [issue for issue in before["issues"] if issue not in RECOMPUTABLE]
        if "address_placeholder" in before["issues"] and decision.rule_id != "AICA-99999-v1":
            raise ValueError(
                "Promozione del segnaposto richiede la regola verificata AICA-99999-v1"
            )
        if "municipality" in decision.corrections:
            values["municipality_istat_code"] = None
        row = Intervention.model_validate(values)
        validate_rows([row], original.last_seen_at)
        if row.validation_status != "validated":
            raise ValueError("La revisione non supera i controlli: " + ",".join(row.issues))
        # Una correzione umana non altera mai la stringa originale della fonte.
        if "address" in decision.corrections:
            corrected = Intervention.model_validate(
                row.model_dump()
                | {
                    "address_original": decision.corrections["address"],
                    "address": decision.corrections["address"],
                }
            )
            validate_rows([corrected], original.last_seen_at)
            row.address, row.house_number = corrected.address, corrected.house_number
            row.address_quality = "human_reviewed"
        after = row.model_dump(mode="json")
        # Non retrocedere una proiezione più recente per approvare un vecchio record.
        current = connection.execute(
            "SELECT last_seen_at FROM interventions WHERE intervention_id=?", [row.intervention_id]
        ).fetchone()
        if current and current[0] >= original.last_seen_at:
            raise ValueError("Esiste già un'osservazione uguale o più recente")
    connection.execute("BEGIN TRANSACTION")
    try:
        _insert(
            connection,
            "review_decisions",
            dict(
                decision_id=decision.decision_id,
                review_id=decision.review_id,
                actor=decision.actor,
                decided_at=decision.decided_at,
                action=decision.action,
                expected_payload_hash=decision.expected_payload_hash,
                reason=decision.reason,
                evidence_url=str(decision.evidence_url),
                rule_id=decision.rule_id,
                corrections=decision.corrections,
                before_payload=before,
                after_payload=after,
            ),
        )
        if row:
            review_run = "review:" + decision.decision_id
            _insert(
                connection,
                "ingestion_runs",
                dict(
                    run_id=review_run,
                    fingerprint=digest(decision.model_dump(mode="json")),
                    observed_at=decision.decided_at,
                    status="completed",
                    data_origin=row.data_origin,
                ),
            )
            _insert(
                connection,
                "quality_reports",
                dict(
                    run_id=review_run,
                    report={
                        "kind": "human_review",
                        "decision_id": decision.decision_id,
                        "validated_records": 1,
                        "review_records": 0,
                        "errors": 0,
                        "publication_approved": False,
                    },
                ),
            )
            # Il tempo della decisione non è il tempo di osservazione della fonte.
            store._observe(row, review_run, target[1], original.last_seen_at)
        connection.execute("COMMIT")
        return {
            "decision_id": decision.decision_id,
            "action": decision.action,
            "intervention_id": row.intervention_id if row else None,
        }
    except Exception:
        connection.execute("ROLLBACK")
        raise
