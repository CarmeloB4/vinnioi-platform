"""Fixture generate: TUTTI gli interventi sono inventati a scopo di test.

I nomi dei comuni sono voci dell'anagrafica ISTAT; non indicano eventi reali.
Nessun contenuto AICA è copiato nelle fixture.
"""

import pymupdf

HEADER = ["Pos.", "Cod. Intervento", "Indirizzo", "Tipo / Rete", "Stato", "Impatto"]


def synthetic_pdf(
    pages: list[list[list[str]]],
    *,
    municipality="Agrigento",
    total: int | None = None,
    header: list[str] | None = None,
    title: bool = True,
) -> bytes:
    if total is None:
        total = sum(bool(row[0]) for page in pages for row in page)
    with pymupdf.open() as document:
        for page_number, rows in enumerate(pages):
            page = document.new_page(width=842, height=595)
            page.insert_text((40, 24), "FIXTURE SINTETICA - NON SONO DATI REALI", fontsize=9)
            if title:
                page.insert_text((40, 42), f"Interventi - {municipality.upper()}", fontsize=12)
            if page_number == 0:
                page.insert_text((40, 60), f"Totale interventi: {total}", fontsize=9)
                page.insert_text((40, 75), "Generato il: 01/01/2026 alle 10:00:00", fontsize=9)
            boundaries = [40, 82, 195, 436, 575, 669, 800]
            for index, row in enumerate([header or HEADER, *rows]):
                top = 100 + index * 38
                for column, value in enumerate(row):
                    rect = pymupdf.Rect(boundaries[column], top, boundaries[column + 1], top + 38)
                    page.draw_rect(rect, color=(0, 0, 0), width=0.5)
                    for line, text in enumerate(value.split("\n")):
                        page.insert_text((rect.x0 + 4, top + 12 + line * 11), text, fontsize=8)
        return document.tobytes(no_new_id=True)


def synthetic_row(
    identifier="2026_1",
    *,
    position="1",
    address="VIA TEST SINTETICA 1",
    status="PIANIFICATO",
    network="IDRICA",
) -> list[str]:
    return [position, identifier, address, f"Idrico leggero\n{network}", status, "Zona di test"]
