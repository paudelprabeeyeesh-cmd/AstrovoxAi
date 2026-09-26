import asyncio
import logging
import re
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx

from .crawler import CrawlerConfig, WebCrawler

logger = logging.getLogger(__name__)


def _fetch_worker(url: str, user_agent: str, timeout: int) -> Dict[str, Any]:
    headers = {"User-Agent": user_agent}
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url, headers=headers)
            links = re.findall(r'href=["\'](.*?)["\']', resp.text, re.IGNORECASE)
            normalized = []
            for link in links:
                absolute = urljoin(url, link)
                parsed = urlparse(absolute)
                if parsed.scheme in {"http", "https"}:
                    normalized.append(absolute)
            return {
                "url": url,
                "content": resp.text if resp.status_code == 200 else "",
                "links": normalized,
                "status_code": resp.status_code,
            }
    except Exception as exc:
        logger.warning("Worker fetch failed for %s: %s", url, exc)
        return {"url": url, "content": "", "links": [], "status_code": 0}


@dataclass
class DistributedCrawlerConfig:
    max_depth: int = 3
    max_pages: int = 1000
    num_workers: int = 4
    user_agent: str = "AstrovoxDistributedCrawler/1.0"
    timeout: int = 30
    allowed_domains: List[str] = field(default_factory=list)
    crawl_delay_ms: int = 500


class DistributedCrawler:
    def __init__(self, config: Optional[DistributedCrawlerConfig] = None):
        self.config = config or DistributedCrawlerConfig()
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.results: List[Dict[str, Any]] = []
        self.visited: Set[str] = set()
        self._last_request_ts = 0.0
        logger.info(
            "Distributed crawler initialized with %d workers, max_pages=%d",
            self.config.num_workers,
            self.config.max_pages,
        )

    async def worker(self) -> None:
        while True:
            url = await self.queue.get()
            if url is None:
                break
            if url in self.visited:
                self.queue.task_done()
                continue
            self.visited.add(url)
            result = await asyncio.to_thread(
                _fetch_worker,
                url,
                self.config.user_agent,
                self.config.timeout,
            )
            self.results.append(result)
            self.queue.task_done()

    async def _respect_delay(self) -> None:
        delay = self.config.crawl_delay_ms / 1000.0
        wait = delay - (time.time() - self._last_request_ts)
        if wait > 0:
            await asyncio.sleep(wait)

    async def run(self, seed_urls: List[str]) -> List[Dict[str, Any]]:
        workers = [asyncio.create_task(self.worker()) for _ in range(self.config.num_workers)]
        for url in seed_urls:
            await self.queue.put(url)
        await self.queue.join()
        for _ in range(self.config.num_workers):
            await self.queue.put(None)
        await asyncio.gather(*workers)
        return self.results


class DistributedCrawlerCoordinator:
    def __init__(self, crawler: DistributedCrawler):
        self.crawler = crawler

    async def execute(self, seed_urls: List[str]) -> Dict[str, Any]:
        results = await self.crawler.run(seed_urls)
        return {
            "pages_crawled": len(results),
            "pages": results,
        }
