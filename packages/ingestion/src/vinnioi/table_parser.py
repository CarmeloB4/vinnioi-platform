"""PDF tabellari AICA: usa celle geometriche e parole, non testo a spazi fissi."""

import hashlib
import re
from datetime import UTC, datetime

import pymupdf

from vinnioi.interventions import Intervention, ParseResult
from vinnioi.municipalities import normalize
from vinnioi.quality import NETWORKS, validate_rows

HEADERS = ["pos.", "cod. intervento", "indirizzo", "tipo / rete", "stato", "impatto"]


def _text(words: list, cell) -> str:
    if cell is None:
        return ""
    x0, y0, x1, y1 = cell
    selected = [w for w in words if x0 <= (w[0] + w[2]) / 2 < x1 and y0 <= (w[1] + w[3]) / 2 < y1]
    selected.sort(key=lambda w: (round(w[1], 1), w[0]))
    return " ".join(w[4] for w in selected).strip()


def parse_interventions(
    content: bytes,
    *,
    source_url: str,
    municipality: str,
    observed_at: datetime,
    data_origin: str = "real",
    extracted_at: datetime | None = None,
) -> ParseResult:
    result = ParseResult()
    extracted_at = extracted_at or datetime.now(UTC)
    document_hash = hashlib.sha256(content).hexdigest()
    area = None
    if observed_at.tzinfo is None:
        raise ValueError("Timestamp di osservazione privo di timezone")
    try:
        if not content.startswith(b"%PDF-") or len(content) > 20_000_000:
            raise ValueError("Contenuto non PDF o oltre 20 MB")
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.is_encrypted or not 0 < len(document) <= 100:
                raise ValueError("PDF cifrato, vuoto o oltre 100 pagine")
            # Ogni pagina deve essere riconosciuta; nessuna assenza dedotta da pagine saltate.
            for page_index, page in enumerate(document):
                text = page.get_text()
                if not text.strip():
                    result.errors.append(f"page_{page_index + 1}:no_text")
                    continue
                if page_index == 0:
                    total = re.search(r"Totale interventi:\s*(\d+)", text, re.I)
                    if total:
                        result.expected_rows = int(total[1])
                    generated = re.search(r"Generato il:\s*([^\n]+)", text)
                    if generated:
                        result.document_generated_at = generated[1].strip()
                    title = re.search(r"Interventi\s*-\s*([^\n]+)", text)
                    matches = bool(title and normalize(title[1]) == normalize(municipality))
                    if (
                        title
                        and normalize(title[1]) == "licata extra urbana"
                        and normalize(municipality) == "licata"
                        and source_url.endswith("/interventi_licata_extra_urbana.pdf")
                    ):
                        matches = True
                        area = "extra urbana"
                    if not matches:
                        result.errors.append("municipality_title_mismatch")
                words = page.get_text("words")
                recognized = 0
                for table in page.find_tables().tables:
                    cells = table.rows
                    if not cells:
                        continue
                    header = [normalize(_text(words, cell)) for cell in cells[0].cells]
                    if header != HEADERS:
                        result.errors.append(f"page_{page_index + 1}:unsupported_table")
                        continue
                    recognized += 1
                    for row_index, physical in enumerate(cells[1:], 1):
                        values = [_text(words, cell) for cell in physical.cells]
                        if len(values) != 6:
                            result.errors.append(f"page_{page_index + 1}:invalid_columns")
                            continue
                        pos, code, address, combined, status, _impact = values
                        if not any(values):
                            continue
                        # Riga di continuazione tra pagine: è ammesso solo il nome rete.
                        if not pos and not code and not address and not status:
                            if (
                                combined in NETWORKS
                                and result.rows
                                and not result.rows[-1].network_type
                            ):
                                result.rows[-1].network_type = combined
                            else:
                                result.errors.append(f"page_{page_index + 1}:orphan_continuation")
                            continue
                        issues = []
                        if not re.fullmatch(r"\d{4}_\d+", code):
                            issues.append(
                                "invalid_source_identifier" if code else "missing_source_identifier"
                            )
                        if not pos.isdigit():
                            issues.append("invalid_position")
                        network = next(
                            (n for n in NETWORKS if combined.endswith(" " + n) or combined == n),
                            None,
                        )
                        kind = combined[: -len(network)].strip() if network else combined
                        result.rows.append(
                            Intervention(
                                source_intervention_id=code or None,
                                municipality=municipality,
                                address=address or None,
                                area=area,
                                intervention_type=kind or None,
                                network_type=network,
                                reported_status=status or None,
                                first_seen_at=observed_at,
                                last_seen_at=observed_at,
                                source_url=source_url,
                                document_hash=document_hash,
                                extracted_at=extracted_at,
                                page_number=page_index + 1,
                                row_number=row_index,
                                issues=issues,
                                data_origin=data_origin,
                            )
                        )
                if recognized != 1:
                    result.errors.append(f"page_{page_index + 1}:expected_one_table")
    except (ValueError, RuntimeError) as error:
        result.errors.append(f"pdf_parse_error:{type(error).__name__}")
    if result.expected_rows is None:
        result.errors.append("missing_expected_count")
    elif result.expected_rows != len(result.rows):
        result.errors.append("row_count_mismatch")
    if result.errors:
        for row in result.rows:
            row.issues.append("document_incomplete")
    result.rows = validate_rows(result.rows, observed_at)
    result.complete = not result.errors
    return result
