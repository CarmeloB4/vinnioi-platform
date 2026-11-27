"""Evidenze di copertura con natura del claim, senza equiparare soci e servizio."""

import hashlib
from datetime import date

from bs4 import BeautifulSoup

from vinnioi.aica import discover
from vinnioi.interventions import digest
from vinnioi.municipalities import lookup
from vinnioi.store import _insert


def coverage_evidence(
    *, intervention_index: bytes, calendar: bytes, checked_on: date
) -> list[dict]:
    result = []
    for raw, url, claim, names in [
        (
            intervention_index,
            "https://www.aicaonline.it/interventi-programmati/",
            "document_link_present",
            [d.comune for d in discover(intervention_index.decode("utf-8"))],
        ),
        (
            calendar,
            "https://www.aicaonline.it/turni-idrici-2/",
            "calendar_block_present",
            [
                h.get_text(" ", strip=True).split(" – ", 1)[0]
                for h in BeautifulSoup(calendar, "html.parser").select(".turni-titolo-comune")
            ],
        ),
    ]:
        sha = hashlib.sha256(raw).hexdigest()
        for name in sorted(set(names)):
            municipality = lookup(name)
            if municipality is None:
                continue
            code = municipality["municipality_istat_code"]
            result.append(
                dict(
                    evidence_id=digest([url, sha, code, claim]),
                    municipality_istat_code=code,
                    claim_type=claim,
                    source_url=url,
                    checked_on=checked_on.isoformat(),
                    source_date=None,
                    document_hash=sha,
                    interpretation=(
                        "Presenza documentale osservata; copertura contrattuale non certificata"
                    ),
                )
            )
    return result


def record_coverage(store, evidence: list[dict]):
    for item in evidence:
        if item["claim_type"] not in {"document_link_present", "calendar_block_present"}:
            raise ValueError("Tipo di evidenza non qualificato")
        if not store.connection.execute(
            "SELECT 1 FROM operator_coverage_evidence WHERE evidence_id=?", [item["evidence_id"]]
        ).fetchone():
            _insert(store.connection, "operator_coverage_evidence", item)
    # operator_coverage resta unknown: nessuna deduzione dal dato amministrativo o dall'elenco soci.
