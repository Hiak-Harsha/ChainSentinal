"""Structured logging configuration for ChainSentinel.

Configures standard library logging with:
1. Rotating JSON file handler writing to data/logs/chainsentinel.log
2. Console stream handler with formatted output
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import time
from typing import Any

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for forensic structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Include forensic context fields if attached via `extra`
        for key in ("entity_id", "alert_id", "txid", "case_id", "trace_id", "ip"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging() -> logging.Logger:
    """Initialize root and application loggers."""
    log_dir = Path("data/logs")
    if not log_dir.parent.exists() and Path("../data").exists():
        log_dir = Path("../data/logs")
    elif not log_dir.parent.exists() and (settings.DATA_DIR).exists():
        log_dir = settings.DATA_DIR / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "chainsentinel.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if setup_logging() is called multiple times
    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(JSONFormatter())
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        console_handler = logging.StreamHandler(sys.stdout)
        console_fmt = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_fmt)
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)

    logger = logging.getLogger("chainsentinel")
    logger.info("Structured logging initialized. Log file: %s", log_file)
    return logger
