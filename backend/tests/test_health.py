"""Tests for health and system endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    """Health endpoint should return status ok with version."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["app"] == "ChainSentinel"


@pytest.mark.asyncio
async def test_offline_check(client):
    """Offline check should report air-gapped mode."""
    resp = await client.get("/api/system/offline-check")
    assert resp.status_code == 200
    data = resp.json()
    assert "air_gapped" in data
    assert isinstance(data["air_gapped"], bool)
    assert "measured_at" in data
    assert "total_sockets" in data
    assert "non_loopback_sockets" in data
    assert isinstance(data["non_loopback_connections"], list)
    assert "message" in data
