"""Gunicorn configuration for production deployment."""

import os
import multiprocessing

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()

# Process naming
proc_name = "astravox-ai"

# Server mechanics
daemon = False
pidfile = None
umask = 0
tmp_upload_dir = None

# SSL (configure in production)
keyfile = os.getenv("SSL_KEYFILE")
certfile = os.getenv("SSL_CERTFILE")

# Preload app for memory efficiency
preload_app = True


def on_starting(server):
    """Called just before the master process is initialized."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    pass


def pre_exec(server):
    """Called just before a new master process is forked."""
    pass


def when_ready(server):
    """Called just after the server is started."""
    pass


def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    pass


def worker_abort(worker):
    """Called when a worker receives SIGABRT."""
    pass
