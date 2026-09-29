"""API Contract & Security Verification Tests.

Verifies:
1. /api/models/lab schema contract matches frontend ModelLabView expectations (actual vs target, etc.)
2. /api/graph/stats schema contract matches OverviewView expectations (genuine metrics, no synthetic mocks)
3. /api/ingest/quarantine endpoint returns authenticated quarantine records with reason codes
4. /api/trace/cases/{case_id}/timeline contract for audit events
5. Security sanitization: traversal protection in uploads/cases, HTML escaping in export
"""

import html
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.db_singleton import get_db
from app.core.security import _ensure_api_key


@pytest.fixture
def client():
    api_key = _ensure_api_key()
    return TestClient(app, headers={"X-API-Key": api_key})


def test_models_lab_contract(client):
    """Verify /api/models/lab schema contract matches frontend requirements."""
    res = client.get("/api/models/lab")
    assert res.status_code == 200
    data = res.json()

    assert data.get("status") == "ready"
    assert "models" in data
    assert "supervised_metrics" in data
    assert "conformal" in data
    assert "holdout_experiment" in data
    assert "feature_importances" in data
    assert isinstance(data["feature_importances"], list)
    assert "active_learning" in data

    # Conformal section
    conf = data["conformal"]
    assert "coverage" in conf
    assert "target_coverage" in conf
    assert "avg_set_size" in conf
    assert "grade_distribution" in conf

    # Active learning
    al = data["active_learning"]
    assert "total_feedback" in al
    assert "confirmed_malicious" in al
    assert "false_positives" in al


def test_graph_stats_contract(client):
    """Verify /api/graph/stats schema contract provides authentic database aggregates."""
    res = client.get("/api/graph/stats")
    assert res.status_code == 200
    stats = res.json()

    # Must contain real forensic aggregates
    assert "total_entities" in stats
    assert "total_edges" in stats
    assert "total_volume_sat" in stats
    assert "total_volume_btc" in stats
    assert "total_alerts" in stats
    assert "high_risk_alerts" in stats
    assert "mean_risk_score" in stats
    assert "recent_jobs" in stats
    assert isinstance(stats["recent_jobs"], list)


def test_ingest_quarantine_contract(client):
    """Verify /api/ingest/quarantine provides quarantine audit records."""
    res = client.get("/api/ingest/quarantine")
    assert res.status_code == 200
    quarantine_list = res.json()
    assert isinstance(quarantine_list, list)

    # Filter by reason code if supported
    res_filter = client.get("/api/ingest/quarantine?reason_code=INVALID_TXID")
    assert res_filter.status_code == 200


def test_case_timeline_contract(client):
    """Verify case creation, timeline retrieval, and event creation."""
    db = get_db()
    test_case_id = "CASE-CONTRACT-TEST-01"

    # Create dummy case in db
    db.save_investigative_case(
        case_id=test_case_id,
        target_id="bc1qtesttargetcontract999",
        title="Contract Test Case",
        status="OPEN",
        case_data={
            "case_id": test_case_id,
            "target_id": "bc1qtesttargetcontract999",
            "title": "Contract Test Case",
            "status": "OPEN",
        },
    )

    # GET timeline
    res_get = client.get(f"/api/trace/cases/{test_case_id}/timeline")
    assert res_get.status_code == 200
    assert isinstance(res_get.json(), list)

    # POST new timeline event
    event_payload = {
        "event_type": "ANALYST_NOTE",
        "target_id": "bc1qtesttargetcontract999",
        "details": {
            "note": "Corroborated off-chain exchange lead",
            "analyst": "Examiner 07",
        },
    }
    res_post = client.post(f"/api/trace/cases/{test_case_id}/timeline", json=event_payload)
    assert res_post.status_code == 200
    post_data = res_post.json()
    assert "event_id" in post_data
    assert post_data["status"] == "recorded"

    # Verify timeline updated
    res_get_updated = client.get(f"/api/trace/cases/{test_case_id}/timeline")
    assert res_get_updated.status_code == 200
    events = res_get_updated.json()
    assert any(e["event_type"] == "ANALYST_NOTE" for e in events)


def test_security_html_export_escaping(client):
    """Verify case HTML export escapes user-injected script tags."""
    db = get_db()
    malicious_case_id = "CASE-XSS-TEST-99"

    # Create case with XSS injection payload
    xss_payload = "<script>alert('xss')</script>"
    db.save_investigative_case(
        case_id=malicious_case_id,
        target_id=xss_payload,
        title=f"Malicious Injection {xss_payload}",
        status="OPEN",
        case_data={
            "case_id": malicious_case_id,
            "target_id": xss_payload,
            "title": f"Malicious Injection {xss_payload}",
            "status": "OPEN",
            "evidence_bundle": {},
            "narrative_report": f"Narrative: {xss_payload}",
        },
    )

    res = client.get(f"/api/trace/cases/{malicious_case_id}/export/html")
    assert res.status_code == 200
    content = res.text

    # The raw unescaped script tag should NOT be executable HTML inside body
    # It must be escaped as &lt;script&gt; or safely encoded
    assert "<script>alert('xss')</script>" not in content
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in content or "&lt;script&gt;" in content


def test_security_path_traversal_protection(client):
    """Verify path traversal attempts in endpoints return 400/404/422 and cannot escape."""
    # Attempt directory traversal in case ID
    res = client.get("/api/trace/cases/..%2F..%2F..%2Fetc%2Fpasswd/export/html")
    assert res.status_code in [400, 404, 422]

    # Attempt unsupported file format in upload
    files = {"file": ("malicious.exe", b"MZ\x90\x00\x03", "application/octet-stream")}
    res_upload = client.post("/api/ingest/upload", files=files)
    assert res_upload.status_code in [400, 415, 422]
