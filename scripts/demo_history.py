"""Scenario riproducibile, esclusivamente sintetico. Nessuna richiesta di rete."""

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from vinnioi.datasets import export_datasets
from vinnioi.store import Store
from vinnioi.synthetic import synthetic_pdf, synthetic_row
from vinnioi.table_parser import parse_interventions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/demo-synthetic"))
    args = parser.parse_args()
    database = args.output / "history.duckdb"
    if database.exists():
        parser.error("Usare una directory nuova: non sovrascrivere lo storico esistente")
    url = "https://www.aicaonline.it/interventi_programmati/interventi_agrigento.pdf"
    scenarios = [
        [synthetic_row(), synthetic_row("2026_2", position="2")],
        [synthetic_row(), synthetic_row("2026_2", position="2")],
        [synthetic_row(status="COMPLETATO", address="VIA TEST SINTETICA 2")],
        [synthetic_row("2026_2", status="FORNITURA RIPRISTINATA")],
        [synthetic_row("2026_3", status="STATO NON NOTO"), synthetic_row("", position="2")],
    ]
    store = Store(database)
    reports = []
    try:
        for day, rows in enumerate(scenarios):
            at = datetime(2026, 1, 1, 12, tzinfo=UTC) + timedelta(days=day)
            content = synthetic_pdf([rows])
            result = parse_interventions(
                content,
                source_url=url,
                municipality="Agrigento",
                observed_at=at,
                data_origin="synthetic",
            )
            reports.append(
                store.ingest(
                    [(url, "Agrigento", hashlib.sha256(content).hexdigest(), result)],
                    observed_at=at,
                    run_id=f"synthetic-{day}",
                    data_origin="synthetic",
                )
            )
        snapshot = export_datasets(store, args.output / "exports")
        summary = {
            "data_origin": "synthetic",
            "documents_analyzed": len(scenarios),
            "extracted_observations": sum(r["interventions_extracted"] for r in reports),
            "validated_observations": sum(r["validated_records"] for r in reports),
            "review_records": sum(r["review_records"] for r in reports),
            "document_errors": sum(r["errors"] for r in reports),
            "distinct_validated_interventions": len(store.records()),
            "reports": reports,
        }
        (args.output / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        )
        print(json.dumps({k: v for k, v in summary.items() if k != "reports"}, indent=2))
        print(f"Export locali: {snapshot}")
    finally:
        store.close()


if __name__ == "__main__":
    main()
