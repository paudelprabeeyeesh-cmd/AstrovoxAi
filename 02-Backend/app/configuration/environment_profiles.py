"""Environment profiles for deployment stages."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Environment(Enum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class EnvironmentProfile:
    name: str
    env: Environment
    debug: bool = False
    database_url: str = ""
    redis_url: str = ""
    allowed_origins: List[str] = field(default_factory=list)
    log_level: str = "info"
    enable_metrics: bool = True
    enable_tracing: bool = True
    max_upload_size_mb: int = 50
    default_model: str = "gpt-4o-mini"
    max_tokens_per_request: int = 4096
    rate_limit_requests_per_minute: int = 100


ENVIRONMENT_PROFILES: Dict[str, EnvironmentProfile] = {
    "local": EnvironmentProfile(
        name="local",
        env=Environment.LOCAL,
        debug=True,
        database_url="postgresql://localhost/astrovox_dev",
        redis_url="redis://localhost:6379/0",
        allowed_origins=["http://localhost:5173", "http://localhost:3000"],
        log_level="debug",
        max_upload_size_mb=100,
    ),
    "development": EnvironmentProfile(
        name="development",
        env=Environment.DEVELOPMENT,
        debug=True,
        database_url="postgresql://dev-db/astrovox",
        redis_url="redis://redis-dev:6379/0",
        allowed_origins=["https://dev.astrovox.ai"],
        log_level="debug",
    ),
    "staging": EnvironmentProfile(
        name="staging",
        env=Environment.STAGING,
        debug=False,
        database_url="postgresql://staging-db/astrovox",
        redis_url="redis://redis-staging:6379/0",
        allowed_origins=["https://staging.astrovox.ai"],
        log_level="info",
    ),
    "production": EnvironmentProfile(
        name="production",
        env=Environment.PRODUCTION,
        debug=False,
        database_url="postgresql://prod-db/astrovox",
        redis_url="redis://redis-prod:6379/0",
        allowed_origins=["https://astrovox.ai", "https://app.astrovox.ai"],
        log_level="warning",
        rate_limit_requests_per_minute=60,
    ),
    "test": EnvironmentProfile(
        name="test",
        env=Environment.TEST,
        debug=False,
        database_url="postgresql://localhost/astrovox_test",
        redis_url="redis://localhost:6379/1",
        allowed_origins=[],
        log_level="warning",
    ),
}


class EnvironmentManager:
    _current: Optional[EnvironmentProfile] = None

    @classmethod
    def set_environment(cls, name: str) -> Optional[EnvironmentProfile]:
        profile = ENVIRONMENT_PROFILES.get(name)
        if profile:
            cls._current = profile
        return profile

    @classmethod
    def current(cls) -> Optional[EnvironmentProfile]:
        return cls._current

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        if cls._current:
            return getattr(cls._current, key, default)
        return default
