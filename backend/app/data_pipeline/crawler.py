import logging
from dataclasses import dataclass
from typing import List, Optional
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class CrawlerConfig:
    max_depth: int = 3
    max_pages: int = 100
    user_agent: str = "AstrovoxCrawler/1.0"
    timeout: int = 30
    allowed_domains: List[str] = None

    def __post_init__(self):
        if self.allowed_domains is None:
            self.allowed_domains = []


class WebCrawler:
    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig()
        self.visited = set()
        logger.info("Web crawler initialized")

    async def crawl(self, url: str) -> dict:
        if url in self.visited:
            return {}
        self.visited.add(url)
        logger.info("Crawling %s", url)
        return {"url": url, "content": "", "links": []}

    async def run(self, seed_urls: List[str]):
        for url in seed_urls:
            await self.crawl(url)


class CrawlerPipeline:
    def __init__(self, crawler: WebCrawler):
        self.crawler = crawler

    async def execute(self, seed_urls: List[str]):
        await self.crawler.run(seed_urls)
        return {"pages_crawled": len(self.crawler.visited)}
