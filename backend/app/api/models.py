"""Model management and AI Lab diagnostic REST endpoints."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.db_singleton import get_db
from app.core.events import ForensicEvent, event_bus
from chainsentinel.common.datasets import resolve_registered_ground_truth
from chainsentinel.models.pipeline import ModelPipeline
from chainsentinel.storage.db import DatabaseManager

logger = logging.getLogger("chainsentinel.api.models")
router = APIRouter(prefix="/models", tags=["models"])


class TrainRequest(BaseModel):
    dataset_name: str | None = "default"


class DetectRequest(BaseModel):
    min_risk: float = Field(0.35, ge=0.0, le=1.0, alias="min_risk_score", description="Minimum risk score threshold")
    limit: int = Field(50, ge=1, le=500, description="Maximum alerts to generate")

    model_config = {"populate_by_name": True}


@router.post("/train")
def train_models(request: Request, payload: TrainRequest | None = None) -> dict[str, Any]:
    """Train supervised gradient boost model, calibrate conformal bounds, and fit anomaly detector."""
    db = get_db()
    pipeline = ModelPipeline(db=db, model_dir=settings.MODELS_DIR)
    ds_name = payload.dataset_name if payload and payload.dataset_name else "default"
    gt_path = resolve_registered_ground_truth(ds_name)
    logger.info("Starting model training with dataset %s...", ds_name)
    report = pipeline.train(ground_truth_path=gt_path)
    logger.info("Model training complete.")
    return report


@router.post("/detect")
def run_detection(request: Request, payload: DetectRequest | None = None) -> dict[str, Any]:
    """Run full detection pipeline on all entities in database and return generated alerts."""
    min_risk = payload.min_risk if payload else 0.35
    limit = payload.limit if payload else 50
    db = get_db()
    pipeline = ModelPipeline(db=db, model_dir=settings.MODELS_DIR)
    logger.info("Running detection inference with threshold %s, limit %s", min_risk, limit)
    alerts = pipeline.detect(min_risk_score=min_risk, limit=limit)
    logger.info("Detection complete: %d alerts generated", len(alerts))

    # Broadcast detection complete event
    event_bus.publish_sync(
        ForensicEvent(
            type="detection_complete",
            data={
                "alerts_generated": len(alerts),
                "min_risk_score": min_risk,
                "timestamp": time.time(),
            },
        )
    )

    return {
        "alerts_generated": len(alerts),
        "min_risk_score": min_risk,
        "alerts": alerts,
    }


@router.get("/lab")
def get_model_lab_diagnostics() -> dict[str, Any]:
    """Retrieve comprehensive diagnostic benchmarks, metrics, and hold-out experiments for SOC analysts."""
    db = get_db()
    all_metrics = db.list_model_metrics()

    metrics_map = {m["model_name"]: m["metrics"] for m in all_metrics}

    # If holdout experiment is not yet in DB, run it
    if "holdout_experiment" not in metrics_map:
        pipeline = ModelPipeline(db=db, model_dir=settings.MODELS_DIR)
        holdout = pipeline.evaluate_holdout()
        metrics_map["holdout_experiment"] = holdout

    # Add active learning feedback statistics
    feedback_list = db.list_alert_feedback(limit=500)
    confirmed = sum(1 for f in feedback_list if f.get("analyst_verdict") == "confirmed_malicious")
    false_positives = sum(1 for f in feedback_list if f.get("analyst_verdict") == "false_positive")

    return {
        "status": "ready",
        "models": metrics_map,
        "active_learning": {
            "total_feedback": len(feedback_list),
            "confirmed_malicious": confirmed,
            "false_positives": false_positives,
            "pending_retrain": len(feedback_list) > 0,
        },
    }
