"""
Astravox Logging Module
Provides centralized logging infrastructure with file and console handlers.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")


def _ensure_log_dir() -> None:
    """Create logs directory if it doesn't exist."""
    os.makedirs(LOG_DIR, exist_ok=True)


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup and return a logger instance with both console and file handlers.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Custom log file path (optional)
    
    Returns:
        Configured logger instance
    """
    _ensure_log_dir()
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_format = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file is None:
        log_file = os.path.join(LOG_DIR, "astravox.log")
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger


# Global loggers
app_logger = setup_logger("astravox.app", "INFO")
db_logger = setup_logger("astravox.database", "DEBUG")
ai_logger = setup_logger("astravox.ai", "INFO")
auth_logger = setup_logger("astravox.auth", "INFO")
chat_logger = setup_logger("astravox.chat", "INFO")
api_logger = setup_logger("astravox.api", "INFO")
