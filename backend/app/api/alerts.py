"""Investigative alert REST endpoints conforming to Section 7 NTRO API contract."""

from __future__ import annotations

from typing import Any, Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from chainsentinel.storage.db import DatabaseManager

router = APIRouter(prefix="/alerts", tags=["alerts"])

# Valid triage statuses per NTRO Section 7
VALID_STATUSES = {"NEW", "INVESTIGATING", "ESCALATED", "CLOSED_FALSE_POSITIVE", "RESOLVED"}


class AlertStatusUpdate(BaseModel):
    status: Literal["NEW", "INVESTIGATING", "ESCALATED", "CLOSED_FALSE_POSITIVE", "RESOLVED"] = Field(
        ..., description="Triage status per NTRO Section 7 contract"
    )


@router.get("")
def list_alerts(
    min_priority: float = Query(0.0, ge=0.0, le=1.0, description="Minimum alert priority"),
    min_risk: float = Query(0.0, ge=0.0, le=1.0, description="Minimum composite risk score"),
    status: str | None = Query(None, description="Filter by status (e.g. NEW, INVESTIGATING)"),
    limit: int = Query(50, ge=1, le=200, description="Max alerts to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[dict[str, Any]]:
    """List risk-prioritized investigative alerts."""
    db = DatabaseManager(settings.DB_PATH)
    raw_alerts = db.list_alerts(
        min_priority=min_priority,
        min_risk=min_risk,
        status=status,
        limit=limit,
        offset=offset,
    )
    # Return formatted alert payloads
    return [a.get("alert_data", a) for a in raw_alerts]


@router.get("/{alert_id}")
def get_alert_detail(alert_id: str) -> dict[str, Any]:
    """Retrieve full investigative alert bundle by alert_id."""
    db = DatabaseManager(settings.DB_PATH)
    try:
        alert = db.get_alert(alert_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    return alert.get("alert_data", alert)


@router.post("/{alert_id}/status")
def update_alert_status(alert_id: str, payload: AlertStatusUpdate) -> dict[str, Any]:
    """Update operational triage status of an alert."""
    new_status = payload.status

    db = DatabaseManager(settings.DB_PATH)
    alert = db.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    success = db.update_alert_status(alert_id, new_status)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update alert status.")

    return {
        "alert_id": alert_id,
        "previous_status": alert.get("status"),
        "current_status": new_status,
        "updated": True,
    }
