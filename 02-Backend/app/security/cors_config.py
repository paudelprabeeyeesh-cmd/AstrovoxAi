"""CORS configuration."""

from typing import List, Optional
from dataclasses import dataclass
from fastapi.middleware.cors import CORSMiddleware


@dataclass
class CORSConfig:
    allow_origins: List[str] = None
    allow_credentials: bool = True
    allow_methods: List[str] = None
    allow_headers: List[str] = None
    max_age: int = 600

    def __post_init__(self):
        if self.allow_origins is None:
            self.allow_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
        if self.allow_methods is None:
            self.allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        if self.allow_headers is None:
            self.allow_headers = [
                "Authorization",
                "Content-Type",
                "X-Request-ID",
                "X-CSRF-Token",
            ]


def setup_cors(app, config: Optional[CORSConfig] = None) -> None:
    config = config or CORSConfig()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allow_origins,
        allow_credentials=config.allow_credentials,
        allow_methods=config.allow_methods,
        allow_headers=config.allow_headers,
        max_age=config.max_age,
    )
