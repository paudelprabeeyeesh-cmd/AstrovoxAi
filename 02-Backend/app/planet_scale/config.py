"""Multi-region config and deployment strategy constants."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


@dataclass(frozen=True)
class Region:
    name: str
    provider: str
    primary: bool = False
    vector_db_uri: str = ""
    postgres_uri: str = ""
    redis_uri: str = ""


MULTI_REGION_CONFIG: dict[str, Region] = {
    "us-east-1": Region(
        name="us-east-1",
        provider="aws",
        primary=True,
        postgres_uri=_require_env("PRIMARY_POSTGRES_URI"),
        redis_uri=os.getenv("PRIMARY_REDIS_URI", "redis://redis.us-east-1:6379"),
        vector_db_uri=_require_env("PRIMARY_VECTOR_URI"),
    ),
    "eu-west-1": Region(
        name="eu-west-1",
        provider="aws",
        postgres_uri=_require_env("REPLICA_POSTGRES_URI_EU"),
        redis_uri=os.getenv("REPLICA_REDIS_URI_EU", "redis://redis.eu-west-1:6379"),
        vector_db_uri=_require_env("REPLICA_VECTOR_URI_EU"),
    ),
    "ap-south-1": Region(
        name="ap-south-1",
        provider="aws",
        postgres_uri=_require_env("REPLICA_POSTGRES_URI_AP"),
        redis_uri=os.getenv("REPLICA_REDIS_URI_AP", "redis://redis.ap-south-1:6379"),
        vector_db_uri=_require_env("REPLICA_VECTOR_URI_AP"),
    ),
}

DEPLOYMENT_STRATEGIES: dict[str, dict[str, Any]] = {
    "blue_green": {
        "name": "Blue/Green",
        "description": "Zero-downtime deployment with instant rollback",
        "steps": [
            "Deploy green environment",
            "Run smoke tests on green",
            "Switch traffic to green",
            "Keep blue as instant rollback",
        ],
    },
    "canary": {
        "name": "Canary",
        "description": "Gradual rollout with automatic rollback on errors",
        "stages": [
            {"percentage": 5, "duration_minutes": 10},
            {"percentage": 25, "duration_minutes": 20},
            {"percentage": 50, "duration_minutes": 30},
            {"percentage": 100, "duration_minutes": 60},
        ],
        "auto_rollback_threshold": 0.05,
    },
    "rolling": {
        "name": "Rolling",
        "description": "Gradual replacement with max unavailable",
        "max_unavailable": "25%",
        "max_surge": "25%",
    },
}


def get_primary_region() -> Region:
    for region in MULTI_REGION_CONFIG.values():
        if region.primary:
            return region
    return next(iter(MULTI_REGION_CONFIG.values()))


def get_region(name: str) -> Region:
    return MULTI_REGION_CONFIG[name]


def list_regions() -> list[Region]:
    return list(MULTI_REGION_CONFIG.values())
