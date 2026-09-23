"""Extended concurrency and background job verification tests."""

from __future__ import annotations

import concurrent.futures
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import _ensure_api_key
from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    api_key = _ensure_api_key()
    return TestClient(app, headers={"X-API-Key": api_key})


def test_concurrency_20_parallel_requests(client: TestClient):
    """Fire 20 simultaneous parallel requests to /api/graph/entities and /api/alerts."""
    endpoints = [
        "/api/graph/entities?limit=10",
        "/api/alerts?limit=10",
        "/api/alerts/timeseries?bucket=hour",
        "/api/jobs",
    ] * 5  # 20 requests total

    def _fetch(url: str):
        res = client.get(url)
        return res.status_code, res.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(_fetch, url) for url in endpoints]
        results = [f.result() for f in futures]

    for status_code, body in results:
        # Zero 500 internal server errors (no DuckDB lock errors)
        assert status_code in (200, 404), f"Unexpected status {status_code}: {body}"


def test_background_job_endpoints_return_202(client: TestClient):
    """Verify background job endpoints return 202 Accepted when async_mode=true."""
    # Test POST /api/graph/cluster?async_mode=true
    res_cluster = client.post("/api/graph/cluster?async_mode=true", json={"change_threshold": 0.75})
    assert res_cluster.status_code == 202
    data_cluster = res_cluster.json()
    assert "job_id" in data_cluster
    assert data_cluster["status"] == "started"

    # Test POST /api/correlate/run?async_mode=true
    res_corr = client.post("/api/correlate/run?async_mode=true", json={"time_window_sec": 60.0})
    assert res_corr.status_code == 202
    data_corr = res_corr.json()
    assert "job_id" in data_corr
    assert data_corr["status"] == "started"

    # Test POST /api/models/detect?async_mode=true
    res_detect = client.post("/api/models/detect?async_mode=true", json={"min_risk_score": 0.5})
    assert res_detect.status_code == 202
    data_detect = res_detect.json()
    assert "job_id" in data_detect

    # Poll status for one of the jobs
    job_id = data_cluster["job_id"]
    time.sleep(0.1)
    res_job = client.get(f"/api/jobs/{job_id}")
    assert res_job.status_code == 200
    job_status = res_job.json()
    assert job_status["job_id"] == job_id
    assert job_status["status"] in ("started", "running", "completed")


def test_alerts_timeseries_endpoint(client: TestClient):
    """Verify GET /api/alerts/timeseries returns bucketed list."""
    res = client.get("/api/alerts/timeseries?bucket=hour")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
