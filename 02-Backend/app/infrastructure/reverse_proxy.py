"""Reverse proxy configuration."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ProxyMode(str, Enum):
    NGINX = "nginx"
    KONG = "kong"
    TRAEFIK = "traefik"
    ENVOY = "envoy"


@dataclass
class Route:
    path: str
    target: str
    methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    headers: Dict[str, str] = field(default_factory=dict)
    rate_limit: Optional[int] = None
    cache_ttl: Optional[int] = None
    auth_required: bool = False


@dataclass
class ProxyConfig:
    mode: ProxyMode = ProxyMode.NGINX
    listen_port: int = 443
    ssl_enabled: bool = True
    ssl_cert_path: str = "/etc/ssl/certs/astrovox-tls.crt"
    ssl_key_path: str = "/etc/ssl/private/astrovox-tls.key"
    client_max_body_size: str = "50m"
    proxy_read_timeout: int = 60
    proxy_send_timeout: int = 60


class ReverseProxyManager:
    """Manage reverse proxy configurations."""

    def __init__(self, config: Optional[ProxyConfig] = None) -> None:
        self._config = config or ProxyConfig()
        self._routes: List[Route] = []

    def add_route(self, route: Route) -> None:
        self._routes.append(route)
        logger.info(f"Added route: {route.path} -> {route.target}")

    def remove_route(self, path: str) -> None:
        self._routes = [r for r in self._routes if r.path != path]

    def generate_nginx_config(self) -> str:
        routes_config = ""
        for route in self._routes:
            rate_limit = ""
            if route.rate_limit:
                rate_limit = f"limit_req zone=api burst={route.rate_limit} nodelay;\n  "
            routes_config += f"""
    location {route.path} {{
      {rate_limit}proxy_pass {route.target};
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_connect_timeout {self._config.proxy_read_timeout}s;
      proxy_send_timeout {self._config.proxy_send_timeout}s;
      proxy_read_timeout {self._config.proxy_read_timeout}s;
    }}
"""
        return f"""\
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {{
  worker_connections 1024;
}}

http {{
  log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                  '$status $body_bytes_sent "$http_referer" '
                  '"$http_user_agent" "$http_x_forwarded_for"';

  access_log /var/log/nginx/access.log main;
  sendfile on;
  tcp_nopush on;
  tcp_nodelay on;
  keepalive_timeout 65;
  include /etc/nginx/mime.types;
  default_type application/octet-stream;

  gzip on;
  gzip_vary on;
  gzip_min_length 1024;

  limit_req_zone $binary_remote_addr zone=api:10m rate=120r/m;

  server {{
    listen 80;
    server_name astrovox.ai;
    return 301 https://$host$request_uri;
  }}

  server {{
    listen 443 ssl http2;
    server_name astrovox.ai;

    ssl_certificate {self._config.ssl_cert_path};
    ssl_certificate_key {self._config.ssl_key_path};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size {self._config.client_max_body_size};

    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    {routes_config}
  }}
}}
"""


_proxy_manager: Optional[ReverseProxyManager] = None


def get_proxy_manager() -> ReverseProxyManager:
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ReverseProxyManager()
    return _proxy_manager
