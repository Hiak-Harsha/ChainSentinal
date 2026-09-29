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


import urllib.parse
import uuid

_SENSITIVE_PARAM_NAMES = {"api_key", "token", "password", "secret", "key", "access_token", "auth"}


def _sanitize_query_string(query_string: str) -> str:
    """Scrub sensitive parameter values from logged query strings."""
    if not query_string:
        return ""
    try:
        parsed = urllib.parse.parse_qsl(query_string, keep_blank_values=True)
        sanitized = []
        for k, v in parsed:
            if k.lower() in _SENSITIVE_PARAM_NAMES:
                sanitized.append((k, "[REDACTED]"))
            else:
                sanitized.append((k, v))
        return urllib.parse.urlencode(sanitized)
    except Exception:
        return "[UNPARSEABLE_QUERY]"


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Logs every request with structured JSON, tracking request ID, duration, and scrubbing secrets."""

    def __init__(self, app, audit_dir: Path | None = None):
        super().__init__(app)
        from app.core.config import settings
        self._logger = _setup_audit_logger(audit_dir or (settings.DATA_DIR / "audit"))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id

        # Extract sanitized query string
        sanitized_query = _sanitize_query_string(str(request.url.query)) if request.url.query else ""

        # Extract client provenance safely without logging full token
        api_key = request.headers.get("x-api-key", "")
        auth_hdr = request.headers.get("authorization", "")
        auth_type = "none"
        if "cs_session" in request.cookies:
            auth_type = "session_cookie"
        elif api_key:
            auth_type = "x_api_key"
        elif auth_hdr.lower().startswith("bearer "):
            auth_type = "bearer_token"

        response = await call_next(request)

        duration_ms = round((time.time() - start) * 1000, 2)

        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": sanitized_query,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "client": request.client.host if request.client else "unknown",
            "auth_type": auth_type,
        }

        self._logger.info(json.dumps(record, default=str))

        # Attach request ID to response headers for distributed tracing
        response.headers["X-Request-ID"] = request_id

        # Security Headers for production hardening
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
        
        # CSP: allows self, inline styles, Google fonts, and WebSocket feeds
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )

        # HSTS on secure HTTPS requests
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

