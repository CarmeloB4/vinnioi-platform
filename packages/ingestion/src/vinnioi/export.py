import json
from pathlib import Path

import duckdb
import polars as pl

from vinnioi.models import Record

COLUMNS = list(Record.model_fields)


def export_records(records: list[Record], destination: Path) -> None:
    """Export locale di staging; non include testo integrale o documenti PDF."""
    destination.mkdir(parents=True, exist_ok=True)
    rows = [record.model_dump(mode="json") for record in records]
    schema = {name: pl.String for name in COLUMNS}
    schema.update(review_required=pl.Boolean, redistribution_allowed=pl.Boolean)
    frame = pl.DataFrame(rows, schema=schema, strict=True)
    frame.write_csv(destination / "records.csv")
    frame.write_parquet(destination / "records.parquet")
    (destination / "records.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with duckdb.connect(str(destination / "vinnioi.duckdb")) as connection:
        connection.execute(
            "CREATE OR REPLACE TABLE records AS SELECT * FROM read_parquet(?)",
            [str(destination / "records.parquet")],
        )
