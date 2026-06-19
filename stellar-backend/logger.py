"""
Structured logging with context support.
Provides consistent, parseable log output across all agents and services.
"""
import logging
import sys
from config import get_settings

settings = get_settings()


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured at the app's log level."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False
    return logger
