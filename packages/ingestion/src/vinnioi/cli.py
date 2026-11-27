import argparse
import hashlib
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import httpx

from vinnioi.aica import INDEX_URL, discover, document_id
from vinnioi.export import export_records
from vinnioi.models import Category, Record
from vinnioi.pdf import extract_pdf
from vinnioi.transport import Fetcher


def main():
    parser = argparse.ArgumentParser(description="Acquisizione AICA in staging locale")
    parser.add_argument("--registry", type=Path, default=Path("config/sources.toml"))
    parser.add_argument("--output", type=Path, default=Path("data/staging"))
    parser.add_argument("--limit", type=int, default=1, choices=range(1, 31))
    args = parser.parse_args()
    registry = tomllib.loads(args.registry.read_text())
    if registry["aica"]["acquisition_approved"] is not True:
        parser.error("Fonte AICA non approvata: vedere docs/fonti.md")
    with httpx.Client() as client:
        fetcher = Fetcher(client, approved=registry["aica"]["acquisition_approved"])
        documents = discover(fetcher.fetch(INDEX_URL).decode("utf-8"))
        records = []
        for document in documents[: args.limit]:
            discovered_at = datetime.now(UTC)
            content = fetcher.fetch(document.url)
            parsed = extract_pdf(content)
            digest = hashlib.sha256(content).hexdigest()
            records.append(
                Record(
                    id=document_id(document.url, digest),
                    source_url=document.url,
                    discovered_at=discovered_at,
                    fetched_at=parsed.extracted_at,
                    comune=document.comune,
                    area=document.area,
                    category=Category.PROGRAMMATO,
                    content_sha256=digest,
                )
            )
        export_records(records, args.output)
