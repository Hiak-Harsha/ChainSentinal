"""Concurrency and thread-safety tests for ChainSentinel backend.

Verifies that concurrent parallel API requests to DuckDB-backed routes
do not encounter file locking errors or race conditions.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import _ensure_api_key

client = TestClient(app)
api_key = _ensure_api_key()
headers = {"X-API-Key": api_key}


def test_concurrent_reads():
    """Fire parallel requests to /api/graph/entities, /api/alerts, and /api/health."""
    urls = [
        "/api/health",
        "/api/graph/entities?limit=10",
        "/api/alerts?limit=10",
        "/api/graph/metrics",
        "/api/trace/cases?limit=5",
    ]

    def fetch_url(url: str):
        if url == "/api/health":
            res = client.get(url)
        else:
            res = client.get(url, headers=headers)
        return res.status_code, url

    # Run 25 parallel requests across 10 threads
    tasks = urls * 5
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_url, tasks))

    for status_code, url in results:
        # All requests should return 200 or 404 (if no data), but NEVER 500 (lock conflict)
        assert status_code in (200, 404), f"Failed for {url} with status {status_code}"
