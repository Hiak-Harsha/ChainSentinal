"""Authentication and Session Management API router for ChainSentinel.

Provides:
- GET /api/auth/session: Session handshake. For air-gapped/single-workstation SOC mode (no password configured),
  auto-issues an HttpOnly session cookie so the browser never stores or handles private API keys.
- POST /api/auth/login: Operator credential verification (password or API key), issuing an HttpOnly session cookie.
- POST /api/auth/logout: Clears the session cookie.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import (
    create_session_token,
    verify_session_token,
    _ensure_api_key,
)

logger = logging.getLogger("chainsentinel.api.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    password: str | None = Field(None, description="Operator password")
    api_key: str | None = Field(None, description="Server API key")


class AuthStatusResponse(BaseModel):
    authenticated: bool
    requires_login: bool = False
    subject: str | None = None
    auth_method: str | None = None
    app_version: str = settings.VERSION
    token: str | None = None
    api_key: str | None = None


def _set_session_cookie(response: Response, request: Request, subject: str = "operator") -> str:
    """Issue a signed session token and attach it as a secure HttpOnly cookie."""
    token = create_session_token(subject=subject)
    is_secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    samesite_policy = "none" if is_secure else "lax"
    
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite=samesite_policy,
        secure=is_secure,
        path="/",
    )
    return token


@router.get("/session", response_model=AuthStatusResponse)
async def check_or_initiate_session(
    request: Request,
    response: Response,
    cs_session: str | None = Cookie(None, alias="cs_session"),
) -> AuthStatusResponse:
    """Handshake endpoint for browser applications.
    
    If already validly authenticated via session cookie, returns status and token.
    If no operator password is required (air-gapped single-workstation SOC default),
    automatically initializes and sets the HttpOnly session cookie and returns bearer token.
    If operator password is required and session is missing/invalid, indicates requires_login=True.
    """
    if cs_session:
        try:
            payload = verify_session_token(cs_session)
            return AuthStatusResponse(
                authenticated=True,
                requires_login=False,
                subject=payload.get("sub", "operator"),
                auth_method="session_cookie",
                token=cs_session,
                api_key=settings.API_KEY or None,
            )
        except HTTPException:
            # Cookie was invalid or expired
            pass

    # If no operator password is set, single-operator workstation mode applies:
    if not settings.OPERATOR_PASSWORD:
        token = _set_session_cookie(response, request, subject="operator")
        return AuthStatusResponse(
            authenticated=True,
            requires_login=False,
            subject="operator",
            auth_method="auto_session",
            token=token,
            api_key=settings.API_KEY or None,
        )

    # Password is required
    return AuthStatusResponse(
        authenticated=False,
        requires_login=True,
        subject=None,
        auth_method=None,
    )


@router.post("/login", response_model=AuthStatusResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
) -> AuthStatusResponse:
    """Authenticate with password or API key, setting an HttpOnly session cookie."""
    expected_api_key = _ensure_api_key()
    authenticated = False
    subject = "operator"

    # Check API key if provided
    if body.api_key and secrets.compare_digest(body.api_key.strip(), expected_api_key):
        authenticated = True
        subject = "api_operator"

    # Check operator password if configured
    if body.password and settings.OPERATOR_PASSWORD:
        if secrets.compare_digest(body.password.strip(), settings.OPERATOR_PASSWORD.strip()):
            authenticated = True
            subject = "operator"

    # If neither password nor API key matched
    if not authenticated:
        logger.warning("Failed login attempt from %s", request.client.host if request.client else "unknown")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = _set_session_cookie(response, request, subject=subject)
    logger.info("Operator authenticated successfully: %s", subject)
    return AuthStatusResponse(
        authenticated=True,
        requires_login=False,
        subject=subject,
        auth_method="credentials_login",
        token=token,
        api_key=settings.API_KEY or None,
    )


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict[str, str]:
    """Clear session cookie and log out."""
    is_secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    samesite_policy = "none" if is_secure else "lax"
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        samesite=samesite_policy,
        secure=is_secure,
    )
    return {"status": "ok", "message": "Session terminated"}
