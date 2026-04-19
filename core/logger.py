"""
╔══════════════════════════════════════════════════════════════╗
║          FRIDAY — Logger (core/logger.py)                   ║
║   Centralised logging: console + rotating file handler      ║
╚══════════════════════════════════════════════════════════════╝
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from config import LOG_LEVEL, LOG_TO_FILE, LOG_FILENAME


def get_logger(name: str = "FRIDAY") -> logging.Logger:
    """
    Returns a configured logger instance.
    All modules should call this instead of creating their own loggers.
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # ── Formatter ─────────────────────────────────────────────
    fmt = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Console handler ───────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    # ── Rotating file handler (max 5 MB × 3 backups) ─────────
    if LOG_TO_FILE:
        file_handler = RotatingFileHandler(
            LOG_FILENAME, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger
