"""Validazione deterministica; 'validated' riguarda la struttura, non il servizio."""

import re
from collections import Counter
from datetime import datetime

from vinnioi.interventions import Intervention, ValidationStatus, digest
from vinnioi.municipalities import lookup, normalize

KNOWN_STATUSES = {
    "PIANIFICATO",
    "COMPLETATO",
    "IN CORSO",
    "ANNULLATO",
    "SOSPESO",
    "FORNITURA RIPRISTINATA",
}
NETWORKS = {"IDRICA", "FOGNARIA", "MISTA"}
REQUIRED = (
    "source_intervention_id",
    "municipality_istat_code",
    "address",
    "intervention_type",
    "network_type",
    "reported_status",
)


def validate_rows(rows: list[Intervention], observed_at: datetime) -> list[Intervention]:
    for row in rows:
        issues = set(row.issues)
        municipality = lookup(row.municipality)
        if municipality is None:
            issues.add("unknown_municipality")
        else:
            if row.municipality_istat_code not in (None, municipality["municipality_istat_code"]):
                issues.add("municipality_code_mismatch")
            row.municipality = municipality["municipality"]
            row.municipality_istat_code = municipality["municipality_istat_code"]
            row.province = municipality["province"]
        if not row.source_intervention_id:
            issues.add("missing_source_identifier")
        valid_identifier = bool(
            row.source_intervention_id and re.fullmatch(r"\d{4}_\d+", row.source_intervention_id)
        )
        if row.source_intervention_id and not valid_identifier:
            issues.add("invalid_source_identifier")
        row.intervention_id = None
        if valid_identifier and row.municipality_istat_code:
            row.intervention_id = digest(
                [row.source_id, row.municipality_istat_code, row.source_intervention_id]
            )
        if row.reported_status not in KNOWN_STATUSES:
            issues.add("unknown_status")
        if row.network_type not in NETWORKS:
            issues.add("unknown_network")
        if any(getattr(row, field) is None for field in REQUIRED):
            issues.add("incomplete_record")
        if row.address and ("99999" in row.address or normalize(row.address) in {"nd", "n/d"}):
            issues.add("address_placeholder")
        if row.published_at and row.published_at > observed_at:
            issues.add("publication_in_future")
        if row.resolved_at and (
            row.resolved_at > observed_at
            or (row.scheduled_at and row.resolved_at < row.scheduled_at)
        ):
            issues.add("inconsistent_dates")
        if (
            row.first_seen_at > row.last_seen_at
            or row.extracted_at < row.last_seen_at
            or row.last_seen_at > observed_at
        ):
            issues.add("inconsistent_dates")
        if row.source_id != "aica" or row.source_url.host != "www.aicaonline.it":
            issues.add("invalid_provenance")
        # COMPLETATO indica un lavoro eseguito, non un ripristino della fornitura.
        row.restoration_confirmed = row.reported_status == "FORNITURA RIPRISTINATA"
        if row.resolved_at and not row.restoration_confirmed:
            issues.add("resolution_without_confirmation")
        row.issues = sorted(issues)
    counts = Counter(row.intervention_id for row in rows if row.intervention_id)
    for row in rows:
        if counts[row.intervention_id] > 1:
            row.issues = sorted(set(row.issues) | {"duplicate_identifier"})
        row.validation_status = (
            ValidationStatus.REVIEW if row.issues else ValidationStatus.VALIDATED
        )
    return rows
