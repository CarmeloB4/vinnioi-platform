"""Anagrafica amministrativa ISTAT: nessuna copertura AICA presunta."""

import csv
import unicodedata
from importlib.resources import files


def normalize(value: str) -> str:
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(c)
        )
        .replace("’", "'")
        .split()
    )


def municipalities() -> list[dict[str, str]]:
    resource = files("vinnioi").joinpath("resources/municipalities.csv")
    return list(csv.DictReader(resource.read_text(encoding="utf-8").splitlines()))


def lookup(name: str | None) -> dict[str, str] | None:
    if name is None:
        return None
    return next(
        (row for row in municipalities() if normalize(row["municipality"]) == normalize(name)), None
    )
