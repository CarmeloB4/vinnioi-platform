"""Accesso limitato alle pagine qualificate; approvazione separata per ogni canale."""

import re
from urllib.parse import unquote, urlsplit

import httpx

from vinnioi.transport import Fetcher

CHANNELS = {
    "aica_communications": ("aica", "www.aicaonline.it"),
    "aica_turnations": ("aica", "www.aicaonline.it"),
    "siciliacque_notices": ("siciliacque", "www.siciliacque.it"),
}


def allowed_page(url: str, channel: str) -> bool:
    if channel not in CHANNELS:
        return False
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != CHANNELS[channel][1]
        or parsed.fragment
        or parsed.query
        or "%" in parsed.path
        or any(part in {".", ".."} for part in unquote(parsed.path).split("/"))
    ):
        return False
    if channel == "aica_communications":
        return bool(re.fullmatch(r"/comunicazioni/(?:[a-z0-9-]+/|page/\d+/)?", parsed.path))
    if channel == "aica_turnations":
        return parsed.path in {"/servizi/turni-idrici-settimanali/", "/turni-idrici-2/"}
    # Niente query di ricerca, allegati o aree riservate. Slug WordPress HTML.
    return bool(
        re.fullmatch(r"/(?:avvisi|comunicati-stampa)/(?:[a-z0-9-]+/)?", parsed.path)
    ) and not any(part in parsed.path for part in ("wp-", "login", "privacy"))


class PageFetcher(Fetcher):
    def __init__(self, client: httpx.Client, *, channel: str, approved: bool):
        super().__init__(client, approved)
        if channel not in CHANNELS:
            raise ValueError("Canale non qualificato")
        self.channel = channel

    def fetch(self, url: str) -> bytes:
        if not allowed_page(url, self.channel):
            raise ValueError("Pagina fuori allowlist del canale")
        # Riusa timeout, rate limit e controllo robots senza ampliare l'adattatore PDF.
        from urllib.robotparser import RobotFileParser

        from vinnioi.transport import USER_AGENT

        if self.robots is None:
            host = CHANNELS[self.channel][1]
            raw = self._get(f"https://{host}/robots.txt", 512_000).decode("utf-8")
            if "<html" in raw.lower() or "user-agent:" not in raw.lower():
                raise PermissionError("robots.txt non interpretabile")
            self.robots = RobotFileParser()
            self.robots.parse(raw.splitlines())
        if not self.robots.can_fetch(USER_AGENT, url):
            raise PermissionError("Acquisizione vietata da robots.txt")
        self.delay = max(self.delay, self.robots.crawl_delay(USER_AGENT) or 0)
        return self._get(url, 5_000_000)
