"""Request/response logging middleware with structured JSON logs."""

import logging
import time
import uuid
from typing import Callable, Awaitable

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("astravox.request")