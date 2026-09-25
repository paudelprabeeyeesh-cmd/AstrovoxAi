"""Core configuration management with environment profiles and feature flags."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class DatabaseConfig:
    url: str = "sqlite:///./astrovox.db"
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False


@dataclass
class RedisConfig:
    url: str = "redis://localhost:6379/0"
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5


@dataclass
class VectorDBConfig:
    provider: str = "pgvector"
    url: str = ""
    collection: str = "embeddings"
    dimension: int = 1536
    distance_metric: str = "cosine"


@dataclass
class LLMConfig:
    default_model: str = "gpt-4o-mini"
    fallback_model: str = "gpt-4o"
    expensive_model: str = "o3"
    max_tokens_per_request: int = 100_000
    max_cost_per_request: float = 1.0
    temperature: float = 0.7
    top_p: float = 0.9


@dataclass
class SecurityConfig:
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limit_per_minute: int = 60


@dataclass
class ObservabilityConfig:
    log_level: str = "INFO"
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    otlp_endpoint: str = ""


@dataclass
class FeatureFlags:
    enable_rag: bool = True
    enable_agents: bool = True
    enable_workflows: bool = True
    enable_semantic_cache: bool = True
    enable_cost_tracking: bool = True
    enable_audit_log: bool = True
    enable_pii_redaction: bool = True
    enable_mfa: bool = False
    enable_outcome_pricing: bool = False


@dataclass
class AppConfig:
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)
    api_version: str = "v1"
    app_name: str = "AstrovoxAI"
    app_version: str = "0.1.0"

    @classmethod
    def from_env(cls) -> AppConfig:
        env = Environment(os.getenv("APP_ENV", "development"))
        return cls(
            environment=env,
            debug=env == Environment.DEVELOPMENT,
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL", "sqlite:///./astrovox.db"),
                pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                echo=env == Environment.DEVELOPMENT,
            ),
            redis=RedisConfig(
                url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
            ),
            vector_db=VectorDBConfig(
                provider=os.getenv("VECTOR_DB_PROVIDER", "pgvector"),
                url=os.getenv("VECTOR_DB_URL", ""),
                collection=os.getenv("VECTOR_DB_COLLECTION", "embeddings"),
                dimension=int(os.getenv("VECTOR_DB_DIMENSION", "1536")),
            ),
            llm=LLMConfig(
                default_model=os.getenv("LLM_DEFAULT_MODEL", "gpt-4o-mini"),
                fallback_model=os.getenv("LLM_FALLBACK_MODEL", "gpt-4o"),
                expensive_model=os.getenv("LLM_EXPENSIVE_MODEL", "o3"),
                max_tokens_per_request=int(os.getenv("LLM_MAX_TOKENS", "100000")),
                max_cost_per_request=float(os.getenv("LLM_MAX_COST", "1.0")),
            ),
            security=SecurityConfig(
                secret_key=os.getenv("SECRET_KEY", ""),
                algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
                access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
                refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
                cors_origins=os.getenv("CORS_ORIGINS", "*").split(","),
                rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            ),
            observability=ObservabilityConfig(
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
                tracing_enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
                otlp_endpoint=os.getenv("OTLP_ENDPOINT", ""),
            ),
            feature_flags=FeatureFlags(
                enable_rag=os.getenv("FF_ENABLE_RAG", "true").lower() == "true",
                enable_agents=os.getenv("FF_ENABLE_AGENTS", "true").lower() == "true",
                enable_workflows=os.getenv("FF_ENABLE_WORKFLOWS", "true").lower() == "true",
                enable_semantic_cache=os.getenv("FF_ENABLE_SEMANTIC_CACHE", "true").lower() == "true",
                enable_cost_tracking=os.getenv("FF_ENABLE_COST_TRACKING", "true").lower() == "true",
                enable_audit_log=os.getenv("FF_ENABLE_AUDIT_LOG", "true").lower() == "true",
                enable_pii_redaction=os.getenv("FF_ENABLE_PII_REDACTION", "true").lower() == "true",
                enable_mfa=os.getenv("FF_ENABLE_MFA", "false").lower() == "true",
                enable_outcome_pricing=os.getenv("FF_ENABLE_OUTCOME_PRICING", "false").lower() == "true",
            ),
        )


_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def reset_config() -> None:
    global _config
    _config = None
