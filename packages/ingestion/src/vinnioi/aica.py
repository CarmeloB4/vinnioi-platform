"""Scoperta dei soli PDF di interventi, senza interpretarli come eventi accertati."""

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

INDEX_URL = "https://www.aicaonline.it/interventi-programmati/"


@dataclass(frozen=True)
class Document:
    url: str
    comune: str
    area: str | None = None


def allowed_url(url: str) -> bool:
    parsed = urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "www.aicaonline.it"
        and not parsed.fragment
        and not parsed.query
        and (
            parsed.path == "/interventi-programmati/"
            or (
                parsed.path.startswith("/interventi_programmati/interventi_")
                and parsed.path.endswith(".pdf")
            )
        )
    )


def discover(html: str) -> list[Document]:
    soup = BeautifulSoup(html, "html.parser")
    found = {}
    for anchor in soup.select("a[href]"):
        url = urljoin(INDEX_URL, anchor["href"])
        if not allowed_url(url) or not urlsplit(url).path.endswith(".pdf"):
            continue
        label = re.sub(r"\bPDF\b|[↓↑]", "", anchor.get_text(" ", strip=True)).strip()
        if not label:
            label = unquote(urlsplit(url).path.rsplit("/", 1)[-1])[11:-4].replace("_", " ")
        area = "extra urbana" if "extra urbana" in label.lower() else None
        comune = re.sub(r"\s*\(extra urbana\)", "", label, flags=re.I).strip()
        found[url] = Document(url, comune, area)
    if not found:
        raise ValueError("Nessun PDF di interventi: possibile variazione del markup")
    return list(found.values())


def document_id(url: str, digest: str) -> str:
    return hashlib.sha256(f"{url}\n{digest}".encode()).hexdigest()
