import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from vinnioi.aica import allowed_url

USER_AGENT = "VinnioiBot/0.1 (+https://vinnioi.it)"


class Fetcher:
    """Niente redirect/retry automatici; robots incerto implica arresto."""

    def __init__(self, client: httpx.Client, approved: bool, delay: float = 2):
        if not approved:
            raise PermissionError("Fonte non approvata nel registro: acquisizione disabilitata")
        self.client = client
        self.delay = max(delay, 2)
        self.last_request = 0.0
        self.robots = None

    def _get(self, url: str, limit: int) -> bytes:
        time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        with self.client.stream(
            "GET", url, headers={"User-Agent": USER_AGENT}, follow_redirects=False, timeout=30
        ) as response:
            response.raise_for_status()
            result = bytearray()
            for chunk in response.iter_bytes():
                result.extend(chunk)
                if len(result) > limit:
                    raise ValueError("Risposta oltre il limite consentito")
            return bytes(result)

    def fetch(self, url: str) -> bytes:
        if not allowed_url(url):
            raise ValueError("URL fuori dall'allowlist")
        if self.robots is None:
            origin = f"https://{urlsplit(url).netloc}"
            raw = self._get(origin + "/robots.txt", 512_000).decode("utf-8", errors="strict")
            if "<html" in raw.lower() or "user-agent:" not in raw.lower():
                raise PermissionError("robots.txt non interpretabile: revisione richiesta")
            self.robots = RobotFileParser()
            self.robots.parse(raw.splitlines())
        if not self.robots.can_fetch(USER_AGENT, url):
            raise PermissionError("robots.txt vieta l'acquisizione")
        self.delay = max(self.delay, self.robots.crawl_delay(USER_AGENT) or 0)
        return self._get(url, 20_000_000)
