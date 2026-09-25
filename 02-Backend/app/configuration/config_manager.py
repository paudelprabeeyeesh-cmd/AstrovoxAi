"""Configuration management with environment profiles."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class ConfigProfile:
    name: str
    database_url: str
    redis_url: str
    log_level: str = "info"
    debug: bool = False
    cors_origins: List[str] = field(default_factory=list)
    feature_flags: Dict[str, bool] = field(default_factory=dict)


PROFILES: Dict[str, ConfigProfile] = {
    "development": ConfigProfile(
        name="development",
        database_url="postgresql://localhost/astrovox_dev",
        redis_url="redis://localhost:6379/0",
        log_level="debug",
        debug=True,
        cors_origins=["http://localhost:5173", "http://localhost:3000"],
    ),
    "staging": ConfigProfile(
        name="staging",
        database_url=os.getenv("STAGING_DATABASE_URL", ""),
        redis_url=os.getenv("STAGING_REDIS_URL", ""),
        log_level="info",
        debug=False,
        cors_origins=["https://staging.astrovox.ai"],
    ),
    "production": ConfigProfile(
        name="production",
        database_url=os.getenv("DATABASE_URL", ""),
        redis_url=os.getenv("REDIS_URL", ""),
        log_level="warning",
        debug=False,
        cors_origins=["https://astrovox.ai"],
    ),
    "test": ConfigProfile(
        name="test",
        database_url="postgresql://localhost/astrovox_test",
        redis_url="redis://localhost:6379/1",
        log_level="warning",
        debug=False,
        cors_origins=[],
    ),
}


class ConfigManager:
    _current_env: Environment = Environment.DEVELOPMENT
    _config: Dict[str, Any] = {}

    @classmethod
    def set_environment(cls, env: Environment) -> None:
        cls._current_env = env
        profile = PROFILES.get(env.value)
        if profile:
            cls._config = {
                "environment": env.value,
                "database_url": profile.database_url,
                "redis_url": profile.redis_url,
                "log_level": profile.log_level,
                "debug": profile.debug,
                "cors_origins": profile.cors_origins,
                "feature_flags": profile.feature_flags,
            }

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        env_value = os.getenv(key.upper())
        if env_value is not None:
            return cls._parse_value(env_value)
        return cls._config.get(key, default)

    @classmethod
    def _parse_value(cls, value: str) -> Any:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    @classmethod
    def get_profile(cls) -> Optional[ConfigProfile]:
        return PROFILES.get(cls._current_env.value)

    @classmethod
    def current_environment(cls) -> Environment:
        return cls._current_env


ConfigManager.set_environment(Environment(os.getenv("APP_ENV", "development")))
