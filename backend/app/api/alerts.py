"""Investigative alert REST endpoints conforming to Section 7 NTRO API contract."""

from __future__ import annotations

import logging
import time
from typing import Any, Literal
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.db_singleton import get_db
from app.core.events import ForensicEvent, event_bus

logger = logging.getLogger("chainsentinel.api.alerts")
router = APIRouter(prefix="/alerts", tags=["alerts"])

# Valid triage statuses per NTRO Section 7
VALID_STATUSES = {"NEW", "INVESTIGATING", "ESCALATED", "CLOSED_FALSE_POSITIVE", "RESOLVED"}


class AlertStatusUpdate(BaseModel):
    status: Literal["NEW", "INVESTIGATING", "ESCALATED", "CLOSED_FALSE_POSITIVE", "RESOLVED"] = Field(
        ..., description="Triage status per NTRO Section 7 contract"
    )


class AlertFeedbackPayload(BaseModel):
    verdict: Literal["confirmed_malicious", "false_positive", "needs_review"] = Field(
        ..., description="Analyst ground-truth verdict for active learning"
    )
    notes: str = Field("", max_length=500, description="Analyst explanation or rationale")


@router.get("")
def list_alerts(
    min_priority: float = Query(0.0, ge=0.0, le=1.0, description="Minimum alert priority"),
    min_risk: float = Query(0.0, ge=0.0, le=1.0, description="Minimum composite risk score"),
    status: str | None = Query(None, description="Filter by status (e.g. NEW, INVESTIGATING)"),
    limit: int = Query(50, ge=1, le=200, description="Max alerts to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[dict[str, Any]]:
    """List risk-prioritized investigative alerts."""
    db = get_db()
    raw_alerts = db.list_alerts(
        min_priority=min_priority,
        min_risk=min_risk,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [a.get("alert_data", a) for a in raw_alerts]


@router.get("/timeseries")
def get_alerts_timeseries(bucket: str = Query("hour", description="Time bucket: hour or day")) -> list[dict[str, Any]]:
    """Group alert counts by timestamp bucket for timeseries sparkline visualization."""
    from collections import Counter
    from datetime import datetime, timezone

    db = get_db()
    try:
        rows = db.conn.execute(
            "SELECT created_at FROM alerts WHERE created_at IS NOT NULL ORDER BY created_at ASC"
        ).fetchall()
    except Exception as err:
        logger.warning("Failed querying alert timeseries: %s", err)
        return []

    if not rows:
        return []

    counts: Counter[str] = Counter()
    for (ts,) in rows:
        if not ts:
            continue
        try:
            dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
            if bucket == "day":
                key = dt.strftime("%Y-%m-%d")
            else:
                key = dt.strftime("%Y-%m-%dT%H:00:00Z")
            counts[key] += 1
        except Exception:
            pass

    sorted_items = sorted(counts.items())
    return [{"bucket": k, "count": v} for k, v in sorted_items]


@router.get("/feedback/list")
def list_feedback(limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    """List recent analyst feedback entries."""
    db = get_db()
    return db.list_alert_feedback(limit=limit)


@router.get("/{alert_id}")
def get_alert_detail(alert_id: str) -> dict[str, Any]:
    """Retrieve full investigative alert bundle by alert_id."""
    db = get_db()
    try:
        alert = db.get_alert(alert_id)
    except Exception as err:
        logger.warning("Error querying alert %s: %s", alert_id, err, extra={"alert_id": alert_id})
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    return alert.get("alert_data", alert)


@router.post("/{alert_id}/status")
def update_alert_status(alert_id: str, payload: AlertStatusUpdate) -> dict[str, Any]:
    """Update operational triage status of an alert."""
    new_status = payload.status
    db = get_db()
    alert = db.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    success = db.update_alert_status(alert_id, new_status)
    if not success:
        logger.error("Failed updating alert status in DuckDB for alert %s", alert_id, extra={"alert_id": alert_id})
        raise HTTPException(status_code=500, detail="Failed to update alert status.")

    result = {
        "alert_id": alert_id,
        "previous_status": alert.get("status"),
        "current_status": new_status,
        "updated": True,
    }

    # Broadcast status change across live WebSocket subscribers
    event_bus.publish_sync(
        ForensicEvent(
            type="alert_updated",
            data={
                "alert_id": alert_id,
                "entity_id": alert.get("entity_id"),
                "status": new_status,
                "timestamp": time.time(),
            },
        )
    )

    return result


@router.post("/{alert_id}/feedback")
def submit_alert_feedback(alert_id: str, payload: AlertFeedbackPayload) -> dict[str, Any]:
    """Record analyst verdict (confirmed malicious or false positive) for active learning."""
    db = get_db()
    alert = db.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
    entity_id = alert.get("entity_id", "")
    ts = time.time()

    db.record_alert_feedback(
        feedback_id=feedback_id,
        alert_id=alert_id,
        entity_id=entity_id,
        analyst_verdict=payload.verdict,
        notes=payload.notes,
        timestamp=ts,
    )

    logger.info(
        "Recorded analyst feedback: alert=%s, verdict=%s",
        alert_id, payload.verdict,
        extra={"alert_id": alert_id, "entity_id": entity_id},
    )

    # Broadcast feedback event
    event_bus.publish_sync(
        ForensicEvent(
            type="feedback_received",
            data={
                "feedback_id": feedback_id,
                "alert_id": alert_id,
                "entity_id": entity_id,
                "verdict": payload.verdict,
                "timestamp": ts,
            },
        )
    )

    return {
        "feedback_id": feedback_id,
        "alert_id": alert_id,
        "entity_id": entity_id,
        "verdict": payload.verdict,
        "recorded_at": ts,
        "status": "success",
    }

