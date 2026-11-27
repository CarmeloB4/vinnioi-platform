"""Connettori HTML AICA/Siciliacque e classificazione deterministica conservativa."""

import hashlib
import re
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from vinnioi.interventions import ValidationStatus, digest
from vinnioi.municipalities import municipalities, normalize
from vinnioi.source_http import allowed_page
from vinnioi.water_models import MunicipalityMention, TemporalReference, WaterEvent

MONTHS = dict(
    zip(
        (
            "gennaio febbraio marzo aprile maggio giugno "
            "luglio agosto settembre ottobre novembre dicembre"
        ).split(),
        range(1, 13),
        strict=True,
    )
)
PATTERNS = {
    "guasto": r"\b(?:guasto|rottura|perdita)\b",
    "interruzione": (
        r"\b(?:sara|e|e stata) (?:interrotta|sospesa) la fornitura(?: idrica)?\b|"
        r"\b(?:interruzione (?:della |di )?(?:fornitura|distribuzione)"
        r"|fornitura (?:idrica )?(?:interrotta|sospesa)|disservizi"
        r"|problemi nella distribuzione idrica)\b"
    ),
    "manutenzione_programmata": (
        r"\b(?:manutenzione programmata|lavori programmati"
        r"|intervento programmato)\b"
    ),
    "riduzione_portata": (
        r"\b(?:riduzione (?:della |di )?(?:portata|fornitura|produzione)"
        r"|ridotta (?:del \d+% )?la fornitura)\b"
    ),
    "emergenza_idrica": r"\b(?:emergenza idrica|crisi idrica)\b",
    "potabilita": (
        r"\b(?:acqua non (?:e )?potabile|divieto (?:di uso|d'uso)|non potabilita"
        r"|problemi di potabilita)\b"
    ),
}
RESTORED = (
    r"\b(?:la (?:regolare )?fornitura (?:idrica )?(?:e stata|e"
    r"|risulta) (?:regolarmente )?ripristinata"
    r"|e stata ripristinata la (?:regolare )?fornitura(?: idrica)?)\b"
)
FUTURE = (
    r"\b(?:previst\w*|preved\w*|prevede|prevedono|sara|saranno|domani"
    r"|entro|potra|tornera|torneranno)\b"
)
NEGATION = r"\b(?:non|nessun\w*|sment\w*|esclus\w*)\b"


def parse_date(text: str) -> date | None:
    value = normalize(text)
    numeric = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", value)
    written = re.search(r"\b(\d{1,2}) (" + "|".join(MONTHS) + r") (\d{4})\b", value)
    try:
        if numeric:
            return date(int(numeric[3]), int(numeric[2]), int(numeric[1]))
        if written:
            return date(int(written[3]), MONTHS[written[2]], int(written[1]))
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def discover_articles(html: str, *, index_url: str, channel: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    prefix = "/comunicazioni/" if channel == "aica_communications" else "/avvisi/"
    links = []
    for anchor in soup.select("a[href]"):
        url = urljoin(index_url, anchor["href"])
        if (
            allowed_page(url, channel)
            and prefix in url
            and url.rstrip("/") != index_url.rstrip("/")
        ):
            if "/page/" not in url and url not in links:
                links.append(url)
    if not links:
        raise ValueError("Nessun articolo riconosciuto: indice non qualificato")
    return links


def _article(soup, source_id):
    if source_id == "aica":
        root = soup.select_one("main .contenuto") or soup.select_one("article")
    else:
        root = (
            soup.select_one(".content .wysiwyg-text-reset")
            or soup.select_one(".entry-content")
            or soup.select_one(".single-content")
            or soup.select_one("main")
            or soup.select_one("article")
        )
    if root is None:
        raise ValueError("Corpo articolo non riconosciuto")
    for tag in root.select("nav, footer, aside, script, style, form"):
        tag.decompose()
    title = soup.select_one("h1") or soup.select_one('.breadcrumb-item[aria-current="page"]')
    paragraphs = [
        p.get_text(" ", strip=True)
        for p in root.select("p, li")
        if not p.select_one("a.btn") and not p.find(["p", "li"])
    ]
    if title is None or not paragraphs:
        raise ValueError("Titolo o paragrafi articolo mancanti")
    return title.get_text(" ", strip=True), paragraphs


def parse_article(
    content: bytes, *, source_id: str, source_url: str, acquired_at: datetime, data_origin="real"
) -> WaterEvent | None:
    channel = "aica_communications" if source_id == "aica" else "siciliacque_notices"
    if source_id not in {"aica", "siciliacque"} or not allowed_page(source_url, channel):
        raise ValueError("Provenienza articolo non consentita")
    soup = BeautifulSoup(content, "html.parser")
    title, paragraphs = _article(soup, source_id)
    published_at = None
    published_on = None
    for element in soup.select(
        '[datetime], meta[property="article:published_time"], .data-pub, .post-date'
    ):
        raw = element.get("datetime") or element.get("content") or element.get_text(" ", strip=True)
        try:
            timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if timestamp.tzinfo is not None:
                published_at = timestamp
                published_on = timestamp.date()
                break
        except ValueError:
            pass
        published_on = parse_date(raw) or published_on
    statements = [title, *paragraphs]
    categories, status, temporal, mentions, pipelines = set(), None, [], {}, set()
    confirmed = False
    operating_sentences = []
    for statement in statements:
        for sentence in re.split(r"(?<=[.!?;])\s+", statement):
            text = normalize(sentence)
            negative_text = re.sub(r"\bnon (?:e )?(?:potabile|potabilita)\b", "", text)
            negative = bool(re.search(NEGATION, negative_text))
            planned = bool(re.search(FUTURE, text))
            found = {key for key, pattern in PATTERNS.items() if re.search(pattern, text)}
            restored = bool(re.search(RESTORED, text)) and not negative and not planned
            if negative:
                continue
            if restored:
                categories.add("ripristino_confermato")
                confirmed = True
                status = sentence[:400]
            categories.update(found)
            if found or restored:
                operating_sentences.append(sentence)
                status = status or sentence[:400]
            # Solo date complete o relativi con ancoraggio editoriale verificato.
            tokens = re.finditer(
                r"\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d{1,2} (?:"
                + "|".join(MONTHS)
                + r") \d{4}\b|\bdomani\b|\boggi\b",
                text,
            )
            for token_match in tokens:
                token = token_match[0]
                value = parse_date(token)
                if token in {"oggi", "domani"} and published_on:
                    value = published_on + timedelta(days=token == "domani")
                kind = (
                    "planned"
                    if planned
                    else "actual"
                    if restored or re.search(r"si e verificat|si sono verificat|a causa", text)
                    else "unresolved"
                )
                if token == "domani":
                    kind = "planned"
                elif token == "oggi" and re.search(r"si e verificat|si sono verificat", text):
                    kind = "actual"
                prefix = text[: token_match.start()]
                hour = re.search(r"ore\s+(\d{1,2}(?::\d{2})?)(?:\s+del)?\s*$", prefix)
                temporal.append(
                    TemporalReference(
                        text=token, date=value, kind=kind, time=hour[1] if hour else None
                    )
                )
            for match in re.finditer(
                r"\b(?:acquedotto|condotta)\s+[\"“]?([A-Z][\wÀ-ÿ'-]*(?:[ -][A-Z][\wÀ-ÿ'-]*){0,3})",
                sentence,
            ):
                pipelines.add(match[1].strip('"”.,'))
    if not categories:
        return None  # Editoriale, riepilogo o negazione: nessun evento operativo dedotto.
    for sentence in operating_sentences:
        text = normalize(sentence)
        for municipality in municipalities():
            name = normalize(municipality["municipality"])
            for match in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text):
                if (match.start() and text[match.start() - 1] == "-") or (
                    match.end() < len(text) and text[match.end()] == "-"
                ):
                    continue  # Nome dentro una condotta composta, non un comune coinvolto.
                if text[max(0, match.start() - 15) : match.start()].endswith("provincia di "):
                    continue
                explicit = bool(
                    re.search(r"(?:comun[ei] (?:di )?|\b(?:a|ad|in) )$", text[: match.start()])
                )
                relation = "explicit_service_area" if explicit else "mentioned_only"
                old = mentions.get(municipality["municipality_istat_code"])
                if old is None or explicit:
                    mentions[municipality["municipality_istat_code"]] = MunicipalityMention(
                        istat_code=municipality["municipality_istat_code"],
                        name=municipality["municipality"],
                        relationship=relation,
                        evidence=sentence[:400],
                    )
    if source_id == "siciliacque" and not mentions:
        return None  # Nessuna attribuzione territoriale dal solo nome di una condotta.
    issues = []
    if not mentions:
        issues.append("no_explicit_agrigento_municipality")
    if not any(m.relationship == "explicit_service_area" for m in mentions.values()):
        issues.append("impact_area_requires_review")
    if (published_on and published_on > acquired_at.date()) or (
        published_at and published_at > acquired_at
    ):
        issues.append("publication_in_future")
    if any(t.date is None or t.kind == "unresolved" for t in temporal):
        issues.append("unresolved_temporal_reference")
    if any(t.kind == "actual" and t.date and t.date > acquired_at.date() for t in temporal):
        issues.append("actual_date_in_future")
    if confirmed and len(mentions) > 1:
        issues.append("restoration_scope_requires_review")
    if len({t.date for t in temporal if t.kind == "actual"}) > 1:
        issues.append("multiple_actual_dates")
    return WaterEvent(
        event_id=digest([source_id, source_url]),
        source_id=source_id,
        source_url=source_url,
        document_hash=hashlib.sha256(content).hexdigest(),
        title=title,
        categories=sorted(categories),
        declared_status=status,
        restoration_confirmed=confirmed,
        network_level=(
            "adduction"
            if any(
                re.search(r"acquedotto|adduttore|adduzione|punt[oi] di consegna", normalize(p))
                for p in [title, *paragraphs]
            )
            else "local_distribution"
            if any(
                "distribuzione" in normalize(p) or "rete comunale" in normalize(p)
                for p in paragraphs
            )
            else "unspecified"
        ),
        municipalities=sorted(mentions.values(), key=lambda m: m.istat_code),
        pipelines=sorted(pipelines),
        published_on=published_on,
        published_at=published_at,
        acquired_at=acquired_at,
        extracted_at=datetime.now(UTC),
        temporal_references=temporal,
        issues=issues,
        reliability="needs_review" if issues else "rule_based",
        validation_status=ValidationStatus.REVIEW if issues else ValidationStatus.VALIDATED,
        data_origin=data_origin,
    )
