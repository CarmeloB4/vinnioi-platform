"""Integrazione locale, acquisizione autorizzata, revisione e backup espliciti."""

import argparse
import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import httpx

from vinnioi.backup import LocalStorage, backup, restore
from vinnioi.correlations import record_candidates
from vinnioi.datasets import export_datasets
from vinnioi.events import discover_articles, parse_article
from vinnioi.frontend_data import frontend_preview
from vinnioi.integration_store import ingest_integration
from vinnioi.review import apply_review
from vinnioi.source_http import CHANNELS, PageFetcher, allowed_page
from vinnioi.store import Store
from vinnioi.turnations import parse_calendar
from vinnioi.water_models import ReviewDecision

INDEXES = {
    "aica_communications": "https://www.aicaonline.it/comunicazioni/",
    "siciliacque_notices": "https://www.siciliacque.it/avvisi/",
    "aica_turnations": "https://www.aicaonline.it/turni-idrici-2/",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("--database", type=Path, required=True)
    ingest.add_argument("--output", type=Path, required=True)
    choice = ingest.add_mutually_exclusive_group(required=True)
    choice.add_argument("--manifest", type=Path)
    choice.add_argument("--channel", choices=list(CHANNELS))
    ingest.add_argument("--registry", type=Path, default=Path("config/sources.toml"))
    ingest.add_argument("--observed-at")
    ingest.add_argument("--synthetic", action="store_true")
    ingest.add_argument("--limit", type=int, choices=range(1, 6), default=1)
    ingest.add_argument("--run-id")
    review = sub.add_parser("review")
    review.add_argument("--database", type=Path, required=True)
    review.add_argument("--decision", type=Path, required=True)
    preview = sub.add_parser("preview")
    preview.add_argument("--database", type=Path, required=True)
    preview.add_argument("--output", type=Path, required=True)
    save = sub.add_parser("backup")
    save.add_argument("--database", type=Path, required=True)
    save.add_argument("--snapshot", type=Path, required=True)
    save.add_argument("--storage", type=Path, required=True)
    load = sub.add_parser("restore")
    load.add_argument("--backup-id", required=True)
    load.add_argument("--destination", type=Path, required=True)
    load.add_argument("--storage", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "backup":
        print(backup(args.database, args.snapshot, LocalStorage(args.storage)))
        return
    if args.command == "restore":
        restore(args.backup_id, args.destination, LocalStorage(args.storage))
        return
    if args.command in {"review", "preview"}:
        if not args.database.is_file():
            parser.error("Database non esistente")
        store = Store(args.database)
        try:
            if args.command == "review":
                print(
                    json.dumps(
                        apply_review(
                            store, ReviewDecision.model_validate_json(args.decision.read_text())
                        ),
                        ensure_ascii=False,
                    )
                )
            else:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(frontend_preview(store).model_dump_json(indent=2) + "\n")
        finally:
            store.close()
        return
    if args.synthetic and args.channel:
        parser.error("Le fixture sintetiche non possono acquisire fonti reali")
    if args.manifest and not args.observed_at:
        parser.error("Manifest locale: specificare il tempo effettivo di osservazione")
    at = datetime.fromisoformat(args.observed_at) if args.observed_at else datetime.now(UTC)
    if at.tzinfo is None:
        parser.error("Timestamp senza timezone")
    inputs = []
    if args.manifest:
        for entry in json.loads(args.manifest.read_text()):
            if not allowed_page(entry["source_url"], entry["channel"]):
                parser.error("Manifest fuori allowlist")
            path = (args.manifest.parent / entry["path"]).resolve()
            inputs.append((entry["channel"], entry["source_url"], path.read_bytes()))
    else:
        registry = tomllib.loads(args.registry.read_text())
        if registry.get(args.channel, {}).get("acquisition_approved") is not True:
            parser.error("Canale non approvato: vedere docs/fonti.md")
        try:
            with httpx.Client() as client:
                fetcher = PageFetcher(client, channel=args.channel, approved=True)
                url = INDEXES[args.channel]
                content = fetcher.fetch(url)
                if args.channel == "aica_turnations":
                    inputs.append((args.channel, url, content))
                else:
                    for article in discover_articles(
                        content.decode("utf-8"), index_url=url, channel=args.channel
                    )[: args.limit]:
                        inputs.append((args.channel, article, fetcher.fetch(article)))
        except (httpx.HTTPError, ValueError, PermissionError) as error:
            store = Store(args.database)
            try:
                report = store.record_input_failure(
                    observed_at=datetime.now(UTC),
                    error_type=type(error).__name__,
                    run_id=args.run_id,
                )
                print(json.dumps(report, ensure_ascii=False, indent=2))
                export_datasets(store, args.output)
            finally:
                store.close()
            raise SystemExit(2) from error
        at = datetime.now(UTC)
    if not inputs:
        parser.error("Manifest privo di documenti")
    events, calendars, ignored, errors = [], [], 0, []
    origin = "synthetic" if args.synthetic else "real"
    for channel, url, content in inputs:
        try:
            if channel == "aica_turnations":
                calendars.append(
                    parse_calendar(content, source_url=url, acquired_at=at, data_origin=origin)
                )
            else:
                event = parse_article(
                    content,
                    source_id=CHANNELS[channel][0],
                    source_url=url,
                    acquired_at=at,
                    data_origin=origin,
                )
                if event is None:
                    ignored += 1
                else:
                    events.append(event)
        except ValueError as error:
            errors.append(dict(source_url=url, error=str(error)))
    store = Store(args.database)
    try:
        report = ingest_integration(
            store,
            events=events,
            calendars=calendars,
            observed_at=at,
            run_id=args.run_id,
            data_origin=origin,
            input_errors=errors,
            ignored_articles=ignored,
        )
        report["correlation_candidates"] = len(record_candidates(store))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(export_datasets(store, args.output))
        if errors or report["errors"] or report["review_records"]:
            raise SystemExit(2)
    finally:
        store.close()
