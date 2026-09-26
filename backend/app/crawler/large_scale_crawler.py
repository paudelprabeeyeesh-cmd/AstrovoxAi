import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .crawler import CrawlerConfig, WebCrawler

logger = logging.getLogger(__name__)


@dataclass
class LargeScaleCrawlerConfig:
    max_pages_per_shard: int = 10_000_000
    shard_count: int = 16
    user_agent: str = "AstrovoxLargeScaleCrawler/1.0"
    checkpoint_path: str = "./crawler_checkpoints"
    state_file: str = "./crawler_state.json"
    timeout: int = 30
    crawl_delay_ms: int = 500


class URLShard:
    def __init__(self, shard_id: int, shard_count: int):
        self.shard_id = shard_id
        self.shard_count = shard_count
        self.queue: List[str] = []
        self.completed: set = set()
        self.pages_crawled = 0

    def _shard_of(self, url: str) -> int:
        h = hashlib.md5(url.encode("utf-8")).hexdigest()
        return int(h, 16) % self.shard_count

    def enqueue(self, url: str) -> None:
        if self._shard_of(url) == self.shard_id and url not in self.completed:
            self.queue.append(url)

    def dequeue(self) -> Optional[str]:
        while self.queue:
            url = self.queue.pop(0)
            if url not in self.completed:
                return url
        return None

    def mark_done(self, url: str) -> None:
        self.completed.add(url)
        self.pages_crawled += 1

    def save(self, path: str) -> None:
        data = {
            "shard_id": self.shard_id,
            "queue": self.queue,
            "completed": list(self.completed),
            "pages_crawled": self.pages_crawled,
        }
        with open(os.path.join(path, f"shard_{self.shard_id}.json"), "w") as f:
            json.dump(data, f)

    def load(self, path: str) -> None:
        filepath = os.path.join(path, f"shard_{self.shard_id}.json")
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
            self.queue = data.get("queue", [])
            self.completed = set(data.get("completed", []))
            self.pages_crawled = data.get("pages_crawled", 0)


class LargeScaleCrawler:
    def __init__(self, config: Optional[LargeScaleCrawlerConfig] = None):
        self.config = config or LargeScaleCrawlerConfig()
        self.shards = [
            URLShard(i, self.config.shard_count) for i in range(self.config.shard_count)
        ]
        self.global_visited: set = set()
        self.total_pages = 0
        os.makedirs(self.config.checkpoint_path, exist_ok=True)
        self._load_state()
        logger.info(
            "Large scale crawler initialized: shards=%d, max_per_shard=%d",
            self.config.shard_count,
            self.config.max_pages_per_shard,
        )

    def _load_state(self) -> None:
        if os.path.exists(self.config.state_file):
            try:
                with open(self.config.state_file, "r") as f:
                    state = json.load(f)
                self.global_visited = set(state.get("global_visited", []))
                self.total_pages = state.get("total_pages", 0)
                for shard in self.shards:
                    shard.load(self.config.checkpoint_path)
            except Exception as exc:
                logger.warning("Failed to load crawler state: %s", exc)

    def _save_state(self) -> None:
        try:
            with open(self.config.state_file, "w") as f:
                json.dump(
                    {
                        "global_visited": list(self.global_visited),
                        "total_pages": self.total_pages,
                    },
                    f,
                )
            for shard in self.shards:
                shard.save(self.config.checkpoint_path)
        except Exception as exc:
            logger.warning("Failed to save crawler state: %s", exc)

    def enqueue_seeds(self, urls: List[str]) -> None:
        for url in urls:
            shard = self.shards[self._shard_for(url)]
            shard.enqueue(url)

    def _shard_for(self, url: str) -> "URLShard":
        h = hashlib.md5(url.encode("utf-8")).hexdigest()
        idx = int(h, 16) % self.config.shard_count
        return self.shards[idx]

    def _distribute_links(self, links: List[str]) -> None:
        for link in links:
            if link in self.global_visited:
                continue
            self.global_visited.add(link)
            shard = self._shard_for(link)
            if shard.pages_crawled < self.config.max_pages_per_shard:
                shard.enqueue(link)

    def run_shard(self, shard_id: int) -> Dict[str, Any]:
        shard = self.shards[shard_id]
        crawler = WebCrawler(
            CrawlerConfig(
                max_pages=self.config.max_pages_per_shard,
                user_agent=self.config.user_agent,
                timeout=self.config.timeout,
                crawl_delay_ms=self.config.crawl_delay_ms,
            )
        )
        pages_crawled = 0
        pages = []
        while pages_crawled < self.config.max_pages_per_shard:
            url = shard.dequeue()
            if not url:
                break
            page = crawler.fetch(url)
            if page:
                pages_crawled += 1
                pages.append(page)
                self._distribute_links(page.get("links", []))
            shard.mark_done(url)
        crawler.close()
        shard.pages_crawled += pages_crawled
        self.total_pages += pages_crawled
        return {"shard_id": shard_id, "pages_crawled": pages_crawled, "pages": pages}

    def run(self, seed_urls: List[str]) -> Dict[str, Any]:
        self.enqueue_seeds(seed_urls)
        total_pages = 0
        all_pages = []
        for shard in self.shards:
            if any(shard.queue):
                result = self.run_shard(shard.shard_id)
                total_pages += result["pages_crawled"]
                all_pages.extend(result["pages"])
        self._save_state()
        return {
            "pages_crawled": total_pages,
            "shards": self.config.shard_count,
            "pages": all_pages,
        }
