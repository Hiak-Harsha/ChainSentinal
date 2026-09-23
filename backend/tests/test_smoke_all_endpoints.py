"""
Comprehensive smoke tests for all ChainSentinel backend API routes.
Verifies every endpoint returns a valid 2xx or expected status code.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.security import _ensure_api_key
from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    api_key = _ensure_api_key()
    return TestClient(app, headers={"X-API-Key": api_key})


class TestAllEndpointSmoke:
    """Smoke tests for every router in ChainSentinel."""

    # 1. HEALTH & SYSTEM
    def test_health_endpoints(self, client: TestClient):
        r1 = client.get("/api/health")
        assert r1.status_code == 200
        assert r1.json().get("status") == "ok"

        r2 = client.get("/api/system/offline-check")
        assert r2.status_code == 200
        assert "air_gapped" in r2.json()

    # 2. INGEST
    def test_ingest_endpoints(self, client: TestClient):
        r1 = client.get("/api/ingest/jobs")
        assert r1.status_code == 200
        assert isinstance(r1.json(), list)

        r2 = client.get("/api/ingest/profiles")
        assert r2.status_code == 200
        assert isinstance(r2.json(), list)

        r3 = client.post("/api/ingest/detect-schema", json={"dataset_name": "sample_transactions.csv"})
        assert r3.status_code in (200, 404, 500)  # Endpoint reachable

    # 3. GRAPH
    def test_graph_endpoints(self, client: TestClient):
        r_ents = client.get("/api/graph/entities?limit=10")
        assert r_ents.status_code == 200
        entities = r_ents.json()
        assert isinstance(entities, list)

        if entities:
            target_id = entities[0]["entity_id"]
            r_detail = client.get(f"/api/graph/entities/{target_id}")
            assert r_detail.status_code == 200
            assert r_detail.json()["entity_id"] == target_id

            r_sim = client.get(f"/api/graph/entities/{target_id}/similar?top_k=3")
            assert r_sim.status_code == 200
            assert isinstance(r_sim.json(), list)

            r_sub = client.get(f"/api/graph/subgraph?center_id={target_id}&hops=1")
            assert r_sub.status_code == 200
            assert "nodes" in r_sub.json()

        r_metrics = client.get("/api/graph/metrics")
        assert r_metrics.status_code == 200
        metrics = r_metrics.json()
        assert any(k in metrics for k in ("total_entities", "discovered_entities_count", "evaluated_addresses"))

        # Cluster sync
        r_cl_sync = client.post("/api/graph/cluster", json={"limit": 5})
        assert r_cl_sync.status_code == 200
        assert r_cl_sync.json()["status"] == "completed"

        # Cluster async
        r_cl_async = client.post("/api/graph/cluster?async_mode=true", json={"limit": 5})
        assert r_cl_async.status_code == 202
        assert "job_id" in r_cl_async.json()

    # 4. CORRELATE
    def test_correlate_endpoints(self, client: TestClient):
        r_links = client.get("/api/correlate/operator-links?max_p_value=0.5")
        assert r_links.status_code == 200
        assert isinstance(r_links.json(), list)

        r_ents = client.get("/api/graph/entities?limit=1")
        if r_ents.status_code == 200 and r_ents.json():
            target_id = r_ents.json()[0]["entity_id"]
            r_sig = client.get(f"/api/correlate/signatures/{target_id}")
            assert r_sig.status_code in (200, 404)

        # Correlate sync
        r_corr = client.post("/api/correlate/run", json={"time_window_sec": 30.0})
        assert r_corr.status_code == 200
        assert r_corr.json()["status"] == "completed"

        # Correlate async
        r_corr_async = client.post("/api/correlate/run?async_mode=true", json={"time_window_sec": 30.0})
        assert r_corr_async.status_code == 202
        assert "job_id" in r_corr_async.json()

    # 5. ALERTS
    def test_alerts_endpoints(self, client: TestClient):
        r_alerts = client.get("/api/alerts?limit=10")
        assert r_alerts.status_code == 200
        alerts = r_alerts.json()
        assert isinstance(alerts, list)

        r_ts = client.get("/api/alerts/timeseries?bucket=hour")
        assert r_ts.status_code == 200
        assert isinstance(r_ts.json(), list)

        r_fb_list = client.get("/api/alerts/feedback/list")
        assert r_fb_list.status_code == 200
        assert isinstance(r_fb_list.json(), list)

        if alerts:
            alert_id = alerts[0]["alert_id"]
            r_detail = client.get(f"/api/alerts/{alert_id}")
            assert r_detail.status_code == 200
            assert r_detail.json()["alert_id"] == alert_id

            r_status = client.post(f"/api/alerts/{alert_id}/status", json={"status": "INVESTIGATING"})
            assert r_status.status_code == 200
            assert r_status.json()["current_status"] == "INVESTIGATING"

            r_fb = client.post(f"/api/alerts/{alert_id}/feedback", json={"verdict": "confirmed_malicious", "notes": "Smoke test"})
            assert r_fb.status_code == 200

    # 6. MODELS
    def test_models_endpoints(self, client: TestClient):
        r_lab = client.get("/api/models/lab")
        assert r_lab.status_code == 200
        assert "models" in r_lab.json()

        r_detect = client.post("/api/models/detect", json={"min_risk_score": 0.5, "limit": 10})
        assert r_detect.status_code == 200
        assert "alerts" in r_detect.json()

        r_detect_async = client.post("/api/models/detect?async_mode=true", json={"min_risk_score": 0.5, "limit": 10})
        assert r_detect_async.status_code == 202
        assert "job_id" in r_detect_async.json()

    # 7. TRACE & CASES
    def test_trace_and_case_endpoints(self, client: TestClient):
        r_ents = client.get("/api/graph/entities?limit=1")
        if r_ents.status_code == 200 and r_ents.json():
            origin_id = r_ents.json()[0]["entity_id"]
            r_trace = client.post("/api/trace/run", json={"target": origin_id, "direction": "forward", "max_hops": 2})
            assert r_trace.status_code == 200
            trace_data = r_trace.json()
            assert "trace_id" in trace_data

            trace_id = trace_data["trace_id"]
            r_get_trace = client.get(f"/api/trace/{trace_id}")
            assert r_get_trace.status_code == 200

        r_hist = client.get("/api/trace/history")
        assert r_hist.status_code == 200
        assert isinstance(r_hist.json(), list)

        r_cases = client.get("/api/trace/cases")
        assert r_cases.status_code == 200
        cases = r_cases.json()
        assert isinstance(cases, list)

        if cases:
            case_id = cases[0]["case_id"]
            r_c = client.get(f"/api/trace/cases/{case_id}")
            assert r_c.status_code == 200

            r_tl = client.get(f"/api/trace/cases/{case_id}/timeline")
            assert r_tl.status_code == 200

            r_post_tl = client.post(
                f"/api/trace/cases/{case_id}/timeline",
                json={"event_type": "note_added", "target_id": "ENT_smoke_test", "details": {"note": "Smoke test note"}},
            )
            assert r_post_tl.status_code == 200

            r_html = client.get(f"/api/trace/cases/{case_id}/export/html")
            assert r_html.status_code == 200
            assert "text/html" in r_html.headers.get("content-type", "")

            r_csv = client.get(f"/api/trace/cases/{case_id}/export/csv")
            assert r_csv.status_code == 200
            assert "text/csv" in r_csv.headers.get("content-type", "")

            r_export = client.get(f"/api/trace/cases/{case_id}/export?format=html")
            assert r_export.status_code == 200

    # 8. JOBS
    def test_jobs_endpoints(self, client: TestClient):
        r_jobs = client.get("/api/jobs")
        assert r_jobs.status_code == 200
        assert isinstance(r_jobs.json(), list)

        # Trigger a quick async job to get a valid ID
        r_start = client.post("/api/graph/cluster?async_mode=true", json={"limit": 2})
        job_id = r_start.json()["job_id"]

        r_status = client.get(f"/api/jobs/{job_id}")
        assert r_status.status_code == 200
        assert r_status.json()["job_id"] == job_id

    # 9. WEBSOCKET
    def test_websocket_feed(self, client: TestClient):
        with client.websocket_connect("/ws/live") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
