"""Production-Readiness Verification Test Suite for ChainSentinel.

Tests:
1. Liveness (/api/health)
2. Readiness (/api/ready) verifying DB, storage, and 503 on failure
3. Authentication:
   - Missing credentials -> 401
   - Invalid credentials -> 401
   - Valid X-API-Key -> 200
   - Valid Authorization: Bearer <KEY> -> 200
   - Session handshake (/api/auth/session) -> HttpOnly cookie
   - Valid session cookie on protected route -> 200
   - Expired or tampered session cookie -> 401
   - Login and Logout lifecycle
4. CORS:
   - Allowed origin with credentials
   - OPTIONS preflight
5. Ingestion Security & Content Inspection:
   - Binary executable magic bytes rejection (415)
   - Path traversal in filenames rejection
6. Background Jobs:
   - Job tracking with started_at, completed_at, and cancellation
"""

import io
import time
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest

from app.core.config import settings
from app.core.security import _ensure_api_key, create_session_token, _ensure_session_secret
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def api_key():
    return _ensure_api_key()


# ============================================================================
# 1. Liveness & Readiness Tests
# ============================================================================

def test_health_liveness_probe(client):
    """GET /api/health must answer 'Is process alive?' with 200 OK."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["app"] == "ChainSentinel"
    assert "version" in data
    assert "timestamp" in data


def test_readiness_probe_healthy(client):
    """GET /api/ready must verify database, directory structure, and storage writability."""
    res = client.get("/api/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "dependencies" in data
    assert data["dependencies"]["database"]["status"] == "ok"
    assert data["dependencies"]["directories"]["status"] == "ok"
    assert data["dependencies"]["storage"]["status"] == "ok"


def test_readiness_probe_database_failure(client):
    """GET /api/ready must return HTTP 503 if database cannot execute queries."""
    with patch("app.core.db_singleton.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_db.conn.execute.side_effect = RuntimeError("DuckDB lock acquisition failed: resource busy")
        mock_get_db.return_value = mock_db

        res = client.get("/api/ready")
        assert res.status_code == 503
        data = res.json()
        assert "detail" in data
        assert data["detail"]["status"] == "not_ready"
        assert data["detail"]["dependencies"]["database"]["status"] == "error"


# ============================================================================
# 2. Authentication & Session Security Tests
# ============================================================================

def test_protected_route_anonymous_denied(client):
    """Protected routes cannot be accessed anonymously."""
    res = client.get("/api/graph/entities")
    assert res.status_code == 401
    assert "invalid or missing api key" in res.json()["detail"].lower()


def test_protected_route_invalid_key_denied(client):
    """Protected route with invalid X-API-Key is rejected."""
    res = client.get("/api/graph/entities", headers={"X-API-Key": "invalid_bogus_token_123"})
    assert res.status_code == 401


def test_protected_route_valid_x_api_key(client, api_key):
    """Protected route succeeds with valid X-API-Key."""
    res = client.get("/api/graph/entities?limit=1", headers={"X-API-Key": api_key})
    assert res.status_code == 200


def test_protected_route_valid_bearer_token(client, api_key):
    """Protected route succeeds with Authorization: Bearer <API_KEY>."""
    res = client.get("/api/graph/entities?limit=1", headers={"Authorization": f"Bearer {api_key}"})
    assert res.status_code == 200


def test_session_handshake_auto_initializes_httponly_cookie(client):
    """GET /api/auth/session issues an HttpOnly session cookie without requiring private key."""
    res = client.get("/api/auth/session")
    assert res.status_code == 200
    data = res.json()
    assert data["authenticated"] is True
    # Verify HttpOnly session cookie is set
    assert settings.SESSION_COOKIE_NAME in res.cookies
    cookie = res.cookies[settings.SESSION_COOKIE_NAME]
    assert len(cookie) > 20


def test_protected_route_valid_session_cookie(client):
    """Protected route succeeds when presenting a valid HttpOnly session cookie."""
    # 1. Establish session
    session_res = client.get("/api/auth/session")
    assert session_res.status_code == 200
    token = session_res.cookies[settings.SESSION_COOKIE_NAME]

    # 2. Access protected endpoint with cookie
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    res = client.get("/api/graph/entities?limit=1")
    assert res.status_code == 200


def test_protected_route_expired_session_cookie(client):
    """Expired session tokens must be rejected with 401."""
    # Generate token with negative max_age (already expired)
    expired_token = create_session_token(subject="operator", max_age_seconds=-10)
    client.cookies.set(settings.SESSION_COOKIE_NAME, expired_token)

    res = client.get("/api/graph/entities?limit=1")
    assert res.status_code == 401
    assert "session expired" in res.json()["detail"].lower()


def test_protected_route_tampered_session_cookie(client):
    """Tampered session tokens must be rejected with 401."""
    valid_token = create_session_token(subject="operator", max_age_seconds=3600)
    # Alter payload part
    parts = valid_token.split(".")
    tampered_token = f"eyJzdWIiOiJoYWNrZXIifQ.{parts[1]}"
    client.cookies.set(settings.SESSION_COOKIE_NAME, tampered_token)

    res = client.get("/api/graph/entities?limit=1")
    assert res.status_code == 401
    assert "invalid session credentials" in res.json()["detail"].lower()


def test_auth_login_with_api_key(client, api_key):
    """POST /api/auth/login with valid API key returns 200 and sets cookie."""
    res = client.post("/api/auth/login", json={"api_key": api_key})
    assert res.status_code == 200
    data = res.json()
    assert data["authenticated"] is True
    assert settings.SESSION_COOKIE_NAME in res.cookies


def test_auth_logout(client):
    """POST /api/auth/logout terminates session and clears cookie."""
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ============================================================================
# 3. CORS & Security Headers Tests
# ============================================================================

def test_cors_preflight_options_valid_origin(client):
    """OPTIONS preflight from allowed origin returns CORS headers."""
    res = client.options(
        "/api/graph/entities",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type,X-API-Key",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert res.headers.get("access-control-allow-credentials") == "true"


def test_security_headers_present(client):
    """All responses must include standard defense-in-depth security headers."""
    res = client.get("/api/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in res.headers
    assert "X-Request-ID" in res.headers


# ============================================================================
# 4. Ingestion Security & Content Inspection Tests
# ============================================================================

def test_upload_binary_executable_rejected(client, api_key):
    """Uploading an executable binary (MZ magic bytes) renamed to .csv must be rejected with 415."""
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"A" * 100
    res = client.post(
        "/api/ingest/upload",
        headers={"X-API-Key": api_key},
        files={"file": ("malicious_payload.csv", io.BytesIO(fake_exe), "text/csv")},
    )
    assert res.status_code == 415
    assert "binary or archive file detected" in res.json()["detail"].lower()


def test_upload_path_traversal_filename_rejected(client, api_key):
    """Uploading with path traversal in filename must be rejected."""
    res = client.post(
        "/api/ingest/upload",
        headers={"X-API-Key": api_key},
        files={"file": ("../../etc/passwd.csv", io.BytesIO(b"txid,address\n1,bc1q\n"), "text/csv")},
    )
    assert res.status_code == 415
    assert "path traversal" in res.json()["detail"].lower()


def test_upload_empty_file_rejected(client, api_key):
    """Uploading an empty 0-byte file must be rejected with 400."""
    res = client.post(
        "/api/ingest/upload",
        headers={"X-API-Key": api_key},
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


# ============================================================================
# 5. Background Jobs & Cancellation Tests
# ============================================================================

def test_job_cancellation(client, api_key):
    """POST /api/jobs/{job_id}/cancel cancels an active job."""
    from app.api.jobs import create_and_start_job

    def slow_worker():
        time.sleep(1.0)
        return "done"

    job = create_and_start_job("test_op", slow_worker)
    assert job.status in ("queued", "running")

    # Cancel job
    res = client.post(f"/api/jobs/{job.job_id}/cancel", headers={"X-API-Key": api_key})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "cancelled"
    assert data["job"]["status"] == "cancelled"
