import logging
import os
from logging.handlers import RotatingFileHandler


def configure_logging():
    """Configure centralized logging for the application."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("astravox")
    logger.setLevel(getattr(logging, log_level))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "astravox.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
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
