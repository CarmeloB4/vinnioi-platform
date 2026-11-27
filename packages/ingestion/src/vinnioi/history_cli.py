"""CLI storico: input locali espliciti oppure fonte AICA approvata."""

import argparse
import hashlib
import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import httpx

from vinnioi.aica import INDEX_URL, allowed_url, discover
from vinnioi.datasets import export_datasets
from vinnioi.store import Store
from vinnioi.table_parser import parse_interventions
from vinnioi.transport import Fetcher


def main():
    parser = argparse.ArgumentParser(description="Storico interventi AICA, esclusivamente locale")
    parser.add_argument("--database", type=Path, default=Path("data/history/vinnioi.duckdb"))
    parser.add_argument("--output", type=Path, default=Path("data/exports"))
    parser.add_argument("--run-id")
    parser.add_argument("--manifest", type=Path, help="Manifest locale: documenti già disponibili")
    parser.add_argument("--registry", type=Path, default=Path("config/sources.toml"))
    parser.add_argument("--limit", type=int, default=1, choices=range(1, 31))
    parser.add_argument(
        "--observed-at", help="ISO8601 con timezone; obbligatorio per replay locale"
    )
    parser.add_argument("--synthetic", action="store_true", help="Solo fixture sintetiche")
    parser.add_argument("--export-only", action="store_true")
    args = parser.parse_args()
    if args.export_only:
        if not args.database.exists():
            parser.error("Database storico non esistente")
        store = Store(args.database)
        try:
            print(export_datasets(store, args.output))
        finally:
            store.close()
        return
    now = datetime.fromisoformat(args.observed_at) if args.observed_at else datetime.now(UTC)
    if now.tzinfo is None:
        parser.error("--observed-at richiede timezone")
    data_origin = "synthetic" if args.synthetic else "real"
    documents = []
    registry = None
    if args.manifest:
        if not args.observed_at:
            parser.error(
                "Replay locale: fornire --observed-at effettivo, senza inventare date storiche"
            )
        items = json.loads(args.manifest.read_text())
        for item in items:
            if not allowed_url(item["source_url"]) or not item["source_url"].endswith(".pdf"):
                parser.error("URL del manifest fuori dall'allowlist AICA PDF")
            path = (args.manifest.parent / item["path"]).resolve()
            documents.append((item["source_url"], item["municipality"], path.read_bytes()))
    else:
        if args.synthetic:
            parser.error("--synthetic richiede un manifest locale")
        registry = tomllib.loads(args.registry.read_text())
        if registry["aica"]["acquisition_approved"] is not True:
            parser.error("Fonte AICA non approvata: vedere docs/fonti.md")
        try:
            with httpx.Client() as client:
                fetcher = Fetcher(client, approved=True)
                for document in discover(fetcher.fetch(INDEX_URL).decode("utf-8"))[: args.limit]:
                    documents.append((document.url, document.comune, fetcher.fetch(document.url)))
        except (httpx.HTTPError, ValueError, PermissionError) as error:
            store = Store(args.database)
            try:
                report = store.record_input_failure(
                    observed_at=datetime.now(UTC),
                    error_type=type(error).__name__,
                    run_id=args.run_id,
                )
                export_datasets(store, args.output)
                print(json.dumps(report, ensure_ascii=False, indent=2))
            finally:
                store.close()
            raise SystemExit(2) from error
        # L'osservazione coincide con il completamento dell'acquisizione del batch.
        if not args.observed_at:
            now = datetime.now(UTC)
    if not documents:
        parser.error("Nessun documento: run non avviato")
    parsed = [
        (
            url,
            name,
            hashlib.sha256(content).hexdigest(),
            parse_interventions(
                content, source_url=url, municipality=name, observed_at=now, data_origin=data_origin
            ),
        )
        for url, name, content in documents
    ]
    store = Store(args.database)
    try:
        if registry is not None:
            store.connection.execute(
                "UPDATE sources SET acquisition_approved=?, redistribution_approved=? "
                "WHERE source_id='aica'",
                [
                    registry["aica"]["acquisition_approved"],
                    registry["aica"]["redistribution_approved"],
                ],
            )
        report = store.ingest(parsed, observed_at=now, run_id=args.run_id, data_origin=data_origin)
        snapshot = export_datasets(store, args.output)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"Snapshot locale: {snapshot}")
        if report["errors"] or report["review_records"]:
            raise SystemExit(2)  # Storico/review salvati; nessun fallimento silenzioso in CI.
    finally:
        store.close()
