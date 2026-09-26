import logging
from dataclasses import dataclass
from typing import List, Optional
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class DistributedCrawlerConfig:
    max_depth: int = 3
    max_pages: int = 1000
    num_workers: int = 4
    user_agent: str = "AstrovoxDistributedCrawler/1.0"


class DistributedCrawler:
    def __init__(self, config: Optional[DistributedCrawlerConfig] = None):
        self.config = config or DistributedCrawlerConfig()
        self.queue = asyncio.Queue()
        self.results = []
        logger.info("Distributed crawler initialized with %d workers", self.config.num_workers)

    async def worker(self):
        while True:
            url = await self.queue.get()
            if url is None:
                break
            result = await self._fetch(url)
            self.results.append(result)
            self.queue.task_done()

    async def _fetch(self, url: str) -> dict:
        return {"url": url, "content": "", "status": "ok"}

    async def run(self, seed_urls: List[str]):
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

    async def execute(self, seed_urls: List[str]):
        results = await self.crawler.run(seed_urls)
        return {"pages_crawled": len(results)}
