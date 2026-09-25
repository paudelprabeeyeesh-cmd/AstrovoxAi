"""API versioning middleware and utilities."""

from typing import Dict, Optional, Callable, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from dataclasses import dataclass
from enum import Enum


class APIVersion(Enum):
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"


@dataclass
class VersionedEndpoint:
    path: str
    version: APIVersion
    deprecated: bool = False
    sunset_date: Optional[str] = None


class APIVersionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        version = request.headers.get("API-Version", "v1")
        request.state.api_version = version
        response = await call_next(request)
        response.headers["API-Version"] = version
        return response


class APIVersionRouter:
    _versions: Dict[str, Dict[str, Callable]] = {}

    @classmethod
    def register(cls, version: str, path: str, handler: Callable) -> None:
        if version not in cls._versions:
            cls._versions[version] = {}
        cls._versions[version][path] = handler

    @classmethod
    def get_handler(cls, version: str, path: str) -> Optional[Callable]:
        return cls._versions.get(version, {}).get(path)

    @classmethod
    def list_versions(cls) -> list[str]:
        return list(cls._versions.keys())


VERSIONED_ENDPOINTS = [
    VersionedEndpoint("/v1/chat", APIVersion.V1, deprecated=True),
    VersionedEndpoint("/v2/chat", APIVersion.V2),
    VersionedEndpoint("/v3/chat", APIVersion.V3),
]
