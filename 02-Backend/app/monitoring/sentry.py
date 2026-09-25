"""Sentry error tracking integration."""

from typing import Dict, Any, Optional
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteHttpIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class SentryConfig:
    dsn: str
    environment: str = "production"
    traces_sample_rate: float = 0.1
    profiles_sample_rate: float = 0.1
    release: Optional[str] = None
    send_default_pii: bool = False


class SentryManager:
    _initialized = False

    @classmethod
    def initialize(cls, config: SentryConfig) -> None:
        if cls._initialized:
            return
        sentry_sdk.init(
            dsn=config.dsn,
            environment=config.environment,
            traces_sample_rate=config.traces_sample_rate,
            profiles_sample_rate=config.profiles_sample_rate,
            release=config.release,
            send_default_pii=config.send_default_pii,
            integrations=[
                FastApiIntegration(),
                StarletteHttpIntegration(),
                RedisIntegration(),
                SqlalchemyIntegration(),
            ],
        )
        cls._initialized = True

    @classmethod
    def capture_exception(cls, exc: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)
            sentry_sdk.capture_exception(exc)

    @classmethod
    def capture_message(cls, message: str, level: str = "info") -> None:
        sentry_sdk.capture_message(message, level=level)

    @classmethod
    def set_user(cls, user_id: str, email: Optional[str] = None, username: Optional[str] = None) -> None:
        sentry_sdk.set_user({"id": user_id, "email": email, "username": username})

    @classmethod
    def add_breadcrumb(cls, message: str, category: str = "default", level: str = "info") -> None:
        sentry_sdk.add_breadcrumb(message, category=category, level=level)
