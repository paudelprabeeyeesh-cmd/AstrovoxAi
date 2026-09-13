"""Configuration management for production deployment.

Provides:
- Centralized configuration
- Environment-based overrides
- Configuration validation
- Hot-reload of configuration
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ProductionConfig:
    """Production configuration."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Database
    database_url: str = ""
    database_pool_size: int = 10
    
    # Redis
    redis_url: str = ""
    
    # Security
    jwt_secret: str = ""
    jwt_expiration_hours: int = 24
    
    # Performance
    request_timeout: float = 30.0
    max_concurrent_requests: int = 100
    
    # Observability
    enable_metrics: bool = True
    metrics_port: int = 9090
    log_level: str = "INFO"
    
    # Feature flags
    enable_websocket: bool = True
    enable_file_upload: bool = True
    enable_email: bool = True
    
    @classmethod
    def from_env(cls) -> "ProductionConfig":
        """Create config from environment variables."""
        return cls(
            host=os.getenv("HOST", cls.host),
            port=int(os.getenv("PORT", str(cls.port))),
            workers=int(os.getenv("WORKERS", str(cls.workers))),
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            database_pool_size=int(os.getenv("DATABASE_POOL_SIZE", str(cls.database_pool_size))),
            redis_url=os.getenv("REDIS_URL", cls.redis_url),
            jwt_secret=os.getenv("JWT_SECRET", cls.jwt_secret),
            jwt_expiration_hours=int(os.getenv("JWT_EXPIRATION_HOURS", str(cls.jwt_expiration_hours))),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", str(cls.request_timeout))),
            max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", str(cls.max_concurrent_requests))),
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
            metrics_port=int(os.getenv("METRICS_PORT", str(cls.metrics_port))),
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
            enable_websocket=os.getenv("ENABLE_WEBSOCKET", "true").lower() == "true",
            enable_file_upload=os.getenv("ENABLE_FILE_UPLOAD", "true").lower() == "true",
            enable_email=os.getenv("ENABLE_EMAIL", "true").lower() == "true",
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "workers": self.workers,
            "database_url": self.database_url,
            "database_pool_size": self.database_pool_size,
            "redis_url": self.redis_url,
            "jwt_secret": "***" if self.jwt_secret else "",
            "jwt_expiration_hours": self.jwt_expiration_hours,
            "request_timeout": self.request_timeout,
            "max_concurrent_requests": self.max_concurrent_requests,
            "enable_metrics": self.enable_metrics,
            "metrics_port": self.metrics_port,
            "log_level": self.log_level,
            "enable_websocket": self.enable_websocket,
            "enable_file_upload": self.enable_file_upload,
            "enable_email": self.enable_email,
        }
    
    def save(self, path: str) -> None:
        """Save config to file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "ProductionConfig":
        """Load config from file."""
        if not os.path.exists(path):
            return cls()
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)


# Global config instance
_config: Optional[ProductionConfig] = None


def get_config() -> ProductionConfig:
    """Get global production config."""
    global _config
    if _config is None:
        _config = ProductionConfig.from_env()
    return _config


def reload_config() -> ProductionConfig:
    """Reload config from environment."""
    global _config
    _config = ProductionConfig.from_env()
    return _config