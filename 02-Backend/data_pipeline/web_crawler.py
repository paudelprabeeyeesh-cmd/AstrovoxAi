import hashlib
import math
import re
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass
from typing import Dict
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    import types

    requests = types.ModuleType("requests")

    class _Session:  # type: ignore[no-redef]
        pass

    requests.Session = _Session

USER_AGENT = "AstrovoxCrawler/1.0"


@dataclass
class CrawlConfig:
    delay: float = 1.0
    timeout: int = 10
    max_workers: int = 2
    user_agent: str = USER_AGENT


class DistributedCrawler:
    def __init__(self, config: CrawlConfig | None = None) -> None:
        self.config = config or CrawlConfig()
        self._last_request: Dict[str, float] = {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})

    def _respect_politeness(self, url: str) -> None:
        domain = urlparse(url).netloc
        last = self._last_request.get(domain, 0.0)
        wait = self.config.delay - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_request[domain] = time.time()

    def _allowed_by_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            resp = self.session.get(robots_url, timeout=self.config.timeout)
            rp.parse(resp.text.splitlines())
        except Exception:
            return True
        return rp.can_fetch(self.config.user_agent, url)

    def fetch(self, url: str) -> str | None:
        if self.config.delay > 0:
            self._respect_politeness(url)
        if not self._allowed_by_robots(url):
            return None
        try:
            resp = self.session.get(url, timeout=self.config.timeout)
            resp.raise_for_status()
            return resp.text
        except Exception:
            return None
