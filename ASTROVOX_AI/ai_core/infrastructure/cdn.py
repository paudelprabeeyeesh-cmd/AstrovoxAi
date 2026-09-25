from typing import Optional, Dict, Any, List
import hashlib


class CDN:
    def __init__(self, provider: str = 'cloudflare', cache_ttl: int = 3600):
        self.provider = provider
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, Tuple[bytes, int]] = {}
        self.stats = {'hits': 0, 'misses': 0, 'bytes_served': 0}

    def cache_response(self, key: str, content: bytes, ttl: Optional[int] = None) -> None:
        self.cache[key] = (content, ttl or self.cache_ttl)

    def get(self, key: str) -> Optional[bytes]:
        if key in self.cache:
            content, ttl = self.cache[key]
            self.stats['hits'] += 1
            self.stats['bytes_served'] += len(content)
            return content
        self.stats['misses'] += 1
        return None

    def purge(self, key: str) -> None:
        self.cache.pop(key, None)

    def purge_all(self) -> None:
        self.cache.clear()

    def compute_key(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        key_str = url
        if headers:
            key_str += str(sorted(headers.items()))
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()
