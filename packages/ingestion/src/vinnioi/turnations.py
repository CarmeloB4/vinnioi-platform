"""Calendari AICA HTML. Nessuna data completata usando l'orologio del crawler."""

import hashlib
import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from vinnioi.interventions import ValidationStatus, digest
from vinnioi.municipalities import lookup
from vinnioi.source_http import allowed_page
from vinnioi.water_models import CalendarResult, Turnation


def _iso(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def parse_calendar(
    content: bytes, *, source_url: str, acquired_at: datetime, data_origin="real"
) -> CalendarResult:
    if not allowed_page(source_url, "aica_turnations"):
        raise ValueError("URL calendario non qualificato")
    version = hashlib.sha256(content).hexdigest()
    result = CalendarResult(version=version, source_url=source_url, acquired_at=acquired_at)
    soup = BeautifulSoup(content, "html.parser")
    blocks = soup.select(".turni-comune-blocco")
    if not blocks:
        result.errors.append("calendar_layout_not_recognized")
    seen = set()
    for block_index, block in enumerate(blocks):
        title = block.select_one(".turni-titolo-comune")
        name = title.get_text(" ", strip=True) if title else None
        municipality = lookup(name)
        district = None
        if municipality is None and name and " – " in name:
            base, district = name.split(" – ", 1)
            municipality = lookup(base)  # Sottozone con comune esplicito, mai reti sovracomunali.

        valid_from = _iso(block.get("data-valid-from"))
        valid_until = _iso(block.get("data-valid-until"))
        tables = block.select("table.turni-tabella")
        if not tables:
            result.errors.append("municipality_without_tables")
        for table_index, table in enumerate(tables):
            parent = table.find_parent(class_="turni-serbatoio")
            header = parent.find("h3") if parent else None
            reservoir = header.get_text(" ", strip=True) if header else None
            headers = table.select("thead th")
            if len(headers) < 3 or [h.get_text(" ", strip=True) for h in headers[:2]] != [
                "Zona",
                "Vie servite",
            ]:
                result.errors.append("calendar_header_mismatch")
                continue
            for row_index, physical in enumerate(table.select("tbody tr")):
                cells = physical.find_all("td", recursive=False)
                if len(cells) != len(headers):
                    result.errors.append("calendar_column_mismatch")
                    continue
                zone, streets = (c.get_text(" ", strip=True) for c in cells[:2])
                for column_index, (heading, cell) in enumerate(
                    zip(headers[2:], cells[2:], strict=True)
                ):
                    label = heading.get_text(" ", strip=True)
                    full_date = _iso(heading.get("data-date")) or _iso(label)
                    original = cell.get_text(" ", strip=True) or None
                    time_slot = (
                        original
                        if original
                        and re.fullmatch(
                            r"(?:[01]?\d|2[0-3]):[0-5]\d(?:\s*[-–]\s*(?:[01]?\d|2[0-3]):[0-5]\d)?|H24",
                            original,
                        )
                        else None
                    )
                    issues = []
                    if municipality is None:
                        issues.append("unknown_municipality")
                    if full_date is None:
                        issues.append("calendar_date_incomplete")
                    if not zone:
                        issues.append("incomplete_calendar_location")
                    if (
                        original
                        and time_slot is None
                        and original.casefold() not in {"rinviato", "sospeso"}
                    ):
                        issues.append("unknown_calendar_value")
                    if valid_from and valid_until and valid_until < valid_from:
                        issues.append("invalid_calendar_validity")
                    if full_date and (
                        (valid_from and full_date < valid_from)
                        or (valid_until and full_date > valid_until)
                    ):
                        issues.append("date_outside_validity")
                    identity = [
                        source_url,
                        name,
                        reservoir,
                        zone,
                        str(full_date) if full_date else label,
                        None if full_date else version,
                    ]
                    identifier = digest(identity)
                    if identifier in seen:
                        result.errors.append("duplicate_calendar_slot")
                        identifier = digest(
                            [identifier, block_index, table_index, row_index, column_index]
                        )
                    seen.add(identifier)
                    result.rows.append(
                        Turnation(
                            turnation_id=identifier,
                            source_url=source_url,
                            calendar_version=version,
                            municipality=municipality["municipality"] if municipality else name,
                            municipality_istat_code=municipality["municipality_istat_code"]
                            if municipality
                            else None,
                            municipality_original=name,
                            district=district,
                            source_locator=f"{block_index}:{table_index}:{row_index}:{column_index}",
                            reservoir=reservoir,
                            zone=zone or None,
                            street_description=streets or None,
                            date=full_date,
                            date_label_original=label,
                            time_slot=time_slot,
                            value_original=original,
                            valid_from=valid_from,
                            valid_until=valid_until,
                            notes=original if original and time_slot is None else None,
                            acquired_at=acquired_at,
                            issues=issues,
                            data_origin=data_origin,
                            validation_status=ValidationStatus.REVIEW
                            if issues
                            else ValidationStatus.VALIDATED,
                        )
                    )
    if result.errors:
        for row in result.rows:
            row.issues = sorted(set(row.issues) | {"calendar_incomplete"})
            row.validation_status = ValidationStatus.REVIEW
    result.complete = bool(result.rows) and not result.errors
    return result
