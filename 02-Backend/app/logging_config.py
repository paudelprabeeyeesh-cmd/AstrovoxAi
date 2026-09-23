import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _get_log_path() -> Path:
    """Return a configurable log path and ensure its parent exists."""
    configured_path = os.getenv("LOG_FILE", "logs/astravox.log")
    log_path = Path(configured_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path

def configure_logging():
    """Configure centralized logging for the application."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create logger
    logger = logging.getLogger("astravox")
    logger.setLevel(getattr(logging, log_level))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    
    # File handler (rotating)
    file_handler = RotatingFileHandler(
        _get_log_path(),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(getattr(logging, log_level))
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

# Initialize logger
logger = configure_logging()
