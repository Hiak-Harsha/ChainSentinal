"""Model management and AI Lab diagnostic REST endpoints."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.config import settings
from chainsentinel.models.pipeline import ModelPipeline
from chainsentinel.storage.db import DatabaseManager

router = APIRouter(prefix="/models", tags=["models"])


from chainsentinel.common.datasets import resolve_registered_ground_truth


class TrainRequest(BaseModel):
    dataset_name: str | None = "default"


class DetectRequest(BaseModel):
    min_risk: float = 0.35
    limit: int = 50


@router.post("/train")
def train_models(payload: TrainRequest | None = None) -> dict[str, Any]:
    """Train supervised gradient boost model, calibrate conformal bounds, and fit anomaly detector."""
    db = DatabaseManager(settings.DB_PATH)
    pipeline = ModelPipeline(db=db, model_dir=settings.MODELS_DIR)
    ds_name = payload.dataset_name if payload and payload.dataset_name else "default"
    gt_path = resolve_registered_ground_truth(ds_name)
    report = pipeline.train(ground_truth_path=gt_path)
    return report


@router.post("/detect")
def run_detection(payload: DetectRequest | None = None) -> dict[str, Any]:
    """Run full detection pipeline on all entities in database and return generated alerts."""
    min_risk = payload.min_risk if payload else 0.35
    limit = payload.limit if payload else 50
    db = DatabaseManager(settings.DB_PATH)
    pipeline = ModelPipeline(db=db, model_dir=settings.MODELS_DIR)
    alerts = pipeline.detect(min_risk_score=min_risk, limit=limit)
    return {
        "alerts_generated": len(alerts),
        "min_risk_score": min_risk,
        "alerts": alerts,
    }


@router.get("/lab")
def get_model_lab_diagnostics() -> dict[str, Any]:
    """Retrieve comprehensive diagnostic benchmarks, metrics, and hold-out experiments for SOC analysts."""
    db = DatabaseManager(settings.DB_PATH)
    all_metrics = db.list_model_metrics()

    metrics_map = {m["model_name"]: m["metrics"] for m in all_metrics}

    # If holdout experiment is not yet in DB, run it
    if "holdout_experiment" not in metrics_map:
        pipeline = ModelPipeline(db=db, model_dir=settings.MODELS_DIR)
        holdout = pipeline.evaluate_holdout()
        metrics_map["holdout_experiment"] = holdout

    return {
        "status": "ready",
        "models": metrics_map,
    }
