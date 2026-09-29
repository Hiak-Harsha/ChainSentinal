"""Authentication & Session Security for ChainSentinel.

Supports:
1. Browser Clients: Cryptographically signed HttpOnly session cookie (cs_session).
2. External / Server-to-Server Clients: Authorization: Bearer <API_KEY> or X-API-Key: <API_KEY>.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from pathlib import Path
import secrets
import time
from typing import Any

from fastapi import Cookie, Header, HTTPException, Query, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

from app.core.config import settings

logger = logging.getLogger("chainsentinel.security")

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_api_key_query = APIKeyQuery(name="api_key", auto_error=False)


def _ensure_api_key() -> str:
    """Ensure an API key exists; auto-generate and persist if absent."""
    if settings.API_KEY:
        return settings.API_KEY

    # Auto-generate a secure key
    new_key = secrets.token_urlsafe(32)

    # Persist to .env so it survives restarts
    env_path = Path(".env")
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    lines = [ln for ln in lines if not ln.strip().startswith("CS_API_KEY")]
    lines.append(f"CS_API_KEY={new_key}")
    try:
        env_path.write_text("\n".join(lines) + "\n")
    except Exception as err:
        logger.warning("Could not persist CS_API_KEY to .env: %s", err)

    settings.API_KEY = new_key
    return new_key


def _ensure_session_secret() -> str:
    """Ensure a HMAC secret key exists for signing browser session tokens."""
    if settings.SESSION_SECRET:
        return settings.SESSION_SECRET

    new_secret = secrets.token_hex(32)
    settings.SESSION_SECRET = new_secret
    return new_secret


def create_session_token(subject: str = "operator", max_age_seconds: int | None = None) -> str:
    """Generate a signed HMAC session token."""
    secret = _ensure_session_secret()
    max_age = max_age_seconds or settings.SESSION_MAX_AGE_SECONDS
    now = int(time.time())

    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + max_age,
        "nonce": secrets.token_hex(8),
    }

    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("ascii").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()

    return f"{payload_b64}.{signature}"


def verify_session_token(token: str) -> dict[str, Any]:
    """Verify HMAC signature and expiration on a session token."""
    if not token or "." not in token:
        raise HTTPException(status_code=401, detail="Invalid session credentials")

    parts = token.split(".", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Invalid session credentials")

    payload_b64, signature = parts
    secret = _ensure_session_secret()
    expected_sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()

    if not secrets.compare_digest(signature, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid session credentials")

    # Pad base64 string if necessary
    padding = "=" * ((4 - len(payload_b64) % 4) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session credentials")

    # Verify expiration
    now = int(time.time())
    if payload.get("exp", 0) < now:
        raise HTTPException(status_code=401, detail="Session expired. Please re-authenticate.")

    return payload


async def verify_authentication(
    cs_session: str | None = Cookie(None, alias="cs_session"),
    authorization: str | None = Header(None, alias="Authorization"),
    x_api_key: str | None = Security(_api_key_header),
    api_key_query: str | None = Security(_api_key_query),
) -> dict[str, Any]:
    """FastAPI dependency that validates:
    1. HttpOnly browser session cookie (cs_session)
    2. Authorization: Bearer <API_KEY>
    3. X-API-Key: <API_KEY>
    4. api_key query parameter (for legacy browser tab navigation / direct downloads)
    """
    expected_api_key = _ensure_api_key()

    # 1. Check HttpOnly Session Cookie
    if cs_session:
        try:
            session_payload = verify_session_token(cs_session)
            return {"type": "session", "sub": session_payload.get("sub", "operator")}
        except HTTPException:
            # If cookie was provided but invalid/expired, we fail explicitly
            raise

    # 2. Check Authorization Header (Bearer token)
    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            bearer_token = parts[1]
            if secrets.compare_digest(bearer_token, expected_api_key):
                return {"type": "bearer", "sub": "api_client"}
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # 3. Check X-API-Key Header
    if x_api_key:
        if secrets.compare_digest(x_api_key, expected_api_key):
            return {"type": "x_api_key", "sub": "api_client"}
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # 4. Check Query Parameter (legacy fallback for file downloads)
    if api_key_query:
        if secrets.compare_digest(api_key_query, expected_api_key):
            return {"type": "query_api_key", "sub": "api_client"}
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # No credentials supplied
    raise HTTPException(
        status_code=401,
        detail="Invalid or missing API key",
    )


# Backward-compatible alias for existing route dependencies
verify_api_key = verify_authentication

