"""Structured audit logging middleware for forensic chain-of-custody."""

from __future__ import annotations

import json
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _setup_audit_logger(log_dir: Path) -> logging.Logger:
    """Create a rotating JSON-lines audit logger."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("chainsentinel.audit")
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_dir / "audit.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Logs every request with timestamp, method, path, query params, status, and duration."""

    def __init__(self, app, audit_dir: Path | None = None):
        super().__init__(app)
        from app.core.config import settings
        self._logger = _setup_audit_logger(audit_dir or (settings.DATA_DIR / "audit"))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        
        # Extract API key fingerprint (last 8 chars) for provenance
        api_key = request.headers.get("x-api-key", "")
        key_fingerprint = f"...{api_key[-8:]}" if len(api_key) > 8 else "(none)"

        response = await call_next(request)
        
        duration_ms = round((time.time() - start) * 1000, 2)
        
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query) if request.url.query else "",
            "status": response.status_code,
            "duration_ms": duration_ms,
            "client": request.client.host if request.client else "unknown",
            "key_fingerprint": key_fingerprint,
        }
        
        self._logger.info(json.dumps(record, default=str))
        return response
