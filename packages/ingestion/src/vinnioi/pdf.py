import hashlib
from datetime import UTC, datetime

import pymupdf

from vinnioi.models import PDFText


def extract_pdf(content: bytes, max_pages: int = 100) -> PDFText:
    if not content.startswith(b"%PDF-"):
        raise ValueError("Il contenuto non è un PDF")
    with pymupdf.open(stream=content, filetype="pdf") as doc:
        if doc.is_encrypted or len(doc) > max_pages:
            raise ValueError("PDF cifrato o troppo esteso")
        pages = [page.get_text(sort=True).strip() for page in doc]
    if not any(pages):
        raise ValueError("PDF senza testo: necessaria revisione/OCR, nessun evento generato")
    return PDFText(
        pages=pages,
        content_sha256=hashlib.sha256(content).hexdigest(),
        extracted_at=datetime.now(UTC),
    )
