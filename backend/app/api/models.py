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


from fastapi.responses import JSONResponse
from app.api.jobs import create_and_start_job, update_job


class TrainRequest(BaseModel):
    dataset_name: str | None = "default"
    async_mode: bool = Field(False, description="Run as background job returning 202 Accepted")


class DetectRequest(BaseModel):
    min_risk: float = Field(0.35, ge=0.0, le=1.0, alias="min_risk_score", description="Minimum risk score threshold")
    limit: int = Field(50, ge=1, le=500, description="Maximum alerts to generate")
    async_mode: bool = Field(False, description="Run as background job returning 202 Accepted")

    model_config = {"populate_by_name": True}


def _execute_train_sync(ds_name: str, job_id: str | None = None) -> dict[str, Any]:
    stages = [
        ("loading_features", 0.15),
        ("fitting_classifier", 0.40),
        ("computing_shap", 0.65),
        ("calibrating_conformal", 0.85),
        ("fitting_anomaly_detector", 0.95),
    ]
    for stage_name, prog in stages:
        if job_id:
            update_job(job_id, stage=stage_name, progress=prog)
        event_bus.publish_sync(ForensicEvent(type="training_stage", data={"stage": stage_name, "progress": prog}))
        time.sleep(0.02)

    db = get_db()
    pipeline = ModelPipeline(db=db, model_dir=settings.MODELS_DIR)
    gt_path = resolve_registered_ground_truth(ds_name)
    logger.info("Starting model training with dataset %s...", ds_name)
    report = pipeline.train(ground_truth_path=gt_path)
    logger.info("Model training complete.")

    event_bus.publish_sync(ForensicEvent(type="training_complete", data={"status": "completed", "timestamp": time.time()}))
    return report


def _execute_detect_sync(min_risk: float, limit: int, job_id: str | None = None) -> dict[str, Any]:
    db = get_db()
    if job_id:
        update_job(job_id, stage="running_inference", progress=0.3)
    pipeline = ModelPipeline(db=db, model_dir=settings.MODELS_DIR)
    logger.info("Running detection inference with threshold %s, limit %s", min_risk, limit)
    alerts = pipeline.detect(min_risk_score=min_risk, limit=limit)
    logger.info("Detection complete: %d alerts generated", len(alerts))

    if job_id:
        update_job(job_id, stage="completed", progress=1.0)

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


@router.post("/train")
def train_models(request: Request, payload: TrainRequest | None = None) -> Any:
    """Train supervised gradient boost model, calibrate conformal bounds, and fit anomaly detector."""
    is_async = (
        (payload and payload.async_mode)
        or request.query_params.get("async") == "true"
        or request.query_params.get("async_mode") == "true"
        or request.headers.get("prefer") == "respond-async"
    )
    ds_name = payload.dataset_name if payload and payload.dataset_name else "default"

    if is_async:
        job = create_and_start_job("train_models", _execute_train_sync, ds_name)
        return JSONResponse(status_code=202, content={"job_id": job.job_id, "status": "started"})

    return _execute_train_sync(ds_name)


@router.post("/detect")
def run_detection(request: Request, payload: DetectRequest | None = None) -> Any:
    """Run full detection pipeline on all entities in database and return generated alerts."""
    min_risk = payload.min_risk if payload else 0.35
    limit = payload.limit if payload else 50
    is_async = (
        (payload and payload.async_mode)
        or request.query_params.get("async") == "true"
        or request.query_params.get("async_mode") == "true"
        or request.headers.get("prefer") == "respond-async"
    )

    if is_async:
        job = create_and_start_job("detect", _execute_detect_sync, min_risk, limit)
        return JSONResponse(status_code=202, content={"job_id": job.job_id, "status": "started"})

    return _execute_detect_sync(min_risk, limit)



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
