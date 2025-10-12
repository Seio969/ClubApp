"""Simple application logger helper.

Provides a module-level configured logger and a convenience get_logger()
factory. Logs are written to data/logs/app.log and to stdout during
development. This keeps code that previously used print() consistent and
centralised.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

LOG_DIR = Path(__file__).resolve().parents[2] / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"


def _configure_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # File handler with rotation
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # Stream handler to stdout for interactive use
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(sh)

    # Avoid double logging in root logger
    logger.propagate = False
    return logger


logger = _configure_logger("clubapp")


def get_logger(name: str) -> logging.Logger:
    """Return a child logger for `name` using the application configuration."""
    return logging.getLogger(f"clubapp.{name}") if logging.getLogger(f"clubapp.{name}").handlers else _configure_logger(f"clubapp.{name}")
