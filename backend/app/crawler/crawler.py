import logging
import re
import time
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CrawlerConfig:
    max_depth: int = 3
    max_pages: int = 100
    user_agent: str = "AstrovoxCrawler/1.0"
    timeout: int = 30
    allowed_domains: List[str] = field(default_factory=list)
    respect_robots: bool = True
    crawl_delay_ms: int = 500
    max_retries: int = 2


class WebCrawler:
    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig()
        self.visited: Set[str] = set()
        self.robots_cache: Dict[str, Set[str]] = {}
        self._http = httpx.Client(
            headers={"User-Agent": self.config.user_agent},
            follow_redirects=True,
            timeout=self.config.timeout,
        )
        self._last_request_ts = 0.0
        logger.info("Web crawler initialized with max_pages=%d", self.config.max_pages)

    def _respect_delay(self) -> None:
        delay = self.config.crawl_delay_ms / 1000.0
        wait = delay - (time.time() - self._last_request_ts)
        if wait > 0:
            time.sleep(wait)

    def _allowed_by_robots(self, url: str) -> bool:
        if not self.config.respect_robots:
            return True
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path or "/"
        if domain not in self.robots_cache:
            robots_url = f"{parsed.scheme}://{domain}/robots.txt"
            allowed: Set[str] = set()
            try:
                resp = self._http.get(robots_url)
                if resp.status_code == 200:
                    for line in resp.text.splitlines():
                        if re.match(r"^Disallow:\s*(.*)", line, re.IGNORECASE):
                            prefix = re.match(r"^Disallow:\s*(.*)", line, re.IGNORECASE).group(1).strip()
                            if prefix and prefix != "*":
                                allowed.add(prefix)
            except Exception:
                pass
            self.robots_cache[domain] = allowed
        blocked = self.robots_cache[domain]
        return not any(path.startswith(b) for b in blocked)

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        links = re.findall(r'href=["\'](.*?)["\']', html, re.IGNORECASE)
        normalized = []
        for link in links:
            absolute = urljoin(base_url, link)
            parsed = urlparse(absolute)
            if parsed.scheme in {"http", "https"}:
                normalized.append(absolute)
        return normalized

    def fetch(self, url: str) -> Dict[str, Any]:
        if url in self.visited:
            return {}
        if self.config.allowed_domains:
            parsed = urlparse(url)
            if parsed.netloc.lower() not in {d.lower() for d in self.config.allowed_domains}:
                return {}
        if not self._allowed_by_robots(url):
            return {}

        self._respect_delay()
        for attempt in range(self.config.max_retries):
            try:
                resp = self._http.get(url)
                self._last_request_ts = time.time()
                if resp.status_code == 200:
                    self.visited.add(url)
                    links = self._extract_links(resp.text, url)
                    return {
                        "url": url,
                        "content": resp.text,
                        "links": links,
                        "status_code": resp.status_code,
                    }
            except Exception as exc:
                logger.warning("Fetch failed for %s (attempt %d): %s", url, attempt + 1, exc)
                time.sleep(2 ** attempt)
        return {}

    async def crawl(self, url: str) -> dict:
        return self.fetch(url)

    def run(self, seed_urls: List[str]) -> Dict[str, Any]:
        results = []
        frontier = [(url, 0) for url in seed_urls]
        while frontier and len(results) < self.config.max_pages:
            url, depth = frontier.pop(0)
            if depth > self.config.max_depth:
                continue
            page = self.fetch(url)
            if page:
                results.append(page)
                for link in page.get("links", []):
                    if link not in self.visited:
                        frontier.append((link, depth + 1))
        return {"pages_crawled": len(results), "pages": results}

    def close(self) -> None:
        self._http.close()


class CrawlerPipeline:
    def __init__(self, crawler: WebCrawler):
        self.crawler = crawler

    def execute(self, seed_urls: List[str]) -> Dict[str, Any]:
        result = self.crawler.run(seed_urls)
        return result
