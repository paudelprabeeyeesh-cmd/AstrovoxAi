from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from ..deployment.base_adapter import BaseCloudAdapter, DeploymentConfig


@dataclass
class CDNCacheRule:
    path_pattern: str
    ttl_seconds: int = 86400
    allowed_methods: List[str] = None
    cached_methods: List[str] = None
    query_string: bool = True
    cookies: bool = False

    def __post_init__(self):
        if self.allowed_methods is None:
            self.allowed_methods = ["GET", "HEAD", "OPTIONS"]
        if self.cached_methods is None:
            self.cached_methods = ["GET", "HEAD"]


class CDNManager:
    def __init__(self, adapter: BaseCloudAdapter):
        self.adapter = adapter
        self.cache_rules: List[CDNCacheRule] = []

    def add_cache_rule(self, rule: CDNCacheRule) -> None:
        self.cache_rules.append(rule)

    def get_cache_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "path_pattern": rule.path_pattern,
                "ttl_seconds": rule.ttl_seconds,
                "allowed_methods": rule.allowed_methods,
                "cached_methods": rule.cached_methods,
                "query_string": rule.query_string,
                "cookies": rule.cookies,
            }
            for rule in self.cache_rules
        ]

    def invalidate_cache(self, distribution_id: str, paths: List[str]) -> Dict[str, Any]:
        return self.adapter.invalidate_cdn_cache(distribution_id, paths)

    def apply_cache_rules(self, distribution_id: str) -> Dict[str, Any]:
        rules = self.get_cache_rules()
        return {
            "status": "applied",
            "distribution_id": distribution_id,
            "rules": rules,
        }
