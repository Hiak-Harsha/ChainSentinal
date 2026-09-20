"""API key authentication for air-gapped single-operator deployment."""

from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from app.core.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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

    # Remove any existing CS_API_KEY line
    lines = [ln for ln in lines if not ln.strip().startswith("CS_API_KEY")]
    lines.append(f"CS_API_KEY={new_key}")
    env_path.write_text("\n".join(lines) + "\n")

    # Update the live settings object
    settings.API_KEY = new_key

    import logging
    logger = logging.getLogger("chainsentinel.security")
    logger.warning(
        "═══════════════════════════════════════════════════════\n"
        "  AUTO-GENERATED API KEY (save this for frontend .env):\n"
        "  %s\n"
        "═══════════════════════════════════════════════════════",
        new_key,
    )
    return new_key


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """FastAPI dependency that validates the X-API-Key header."""
    expected = _ensure_api_key()
    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )
    return api_key
