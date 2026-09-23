"""FastAPI router for Network-Blockchain Correlation Engine."""

from __future__ import annotations

from collections import defaultdict
import logging
from pathlib import Path
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.db_singleton import get_db
from app.core.events import ForensicEvent, event_bus
from chainsentinel.common.datasets import resolve_registered_ground_truth
from chainsentinel.correlate.engine import CorrelationEngine
from chainsentinel.eval.correlate_eval import CorrelateEvaluator
from chainsentinel.storage.db import DatabaseManager

logger = logging.getLogger("chainsentinel.api.correlate")
router = APIRouter(prefix="/correlate", tags=["Network Correlation"])


from fastapi.responses import JSONResponse
from app.api.jobs import create_and_start_job, update_job


class CorrelateRunRequest(BaseModel):
    time_window_sec: float = Field(60.0, gt=0, le=3600, description="Temporal correlation window in seconds")
    p_value_thresh: float = Field(0.05, gt=0, le=1.0, description="Significance threshold for permutation test")
    num_permutations: int = Field(100, ge=10, le=10000, description="Number of Monte Carlo permutation rounds")
    dataset_name: str | None = None
    ground_truth_path: str | None = None
    async_mode: bool = Field(False, description="Run as background job returning 202 Accepted")


def _execute_correlate_sync(req_dict: dict[str, Any], job_id: str | None = None) -> dict[str, Any]:
    db = get_db()
    time_window_sec = req_dict.get("time_window_sec", 60.0)
    p_value_thresh = req_dict.get("p_value_thresh", 0.05)
    num_permutations = req_dict.get("num_permutations", 100)
    dataset_name = req_dict.get("dataset_name")
    ground_truth_path = req_dict.get("ground_truth_path")

    if job_id:
        update_job(job_id, stage="computing_timing", progress=0.2)
    event_bus.publish_sync(ForensicEvent(type="correlate_stage", data={"stage": "computing_timing", "progress": 0.2}))

    engine = CorrelationEngine(
        db=db,
        time_window_sec=time_window_sec,
        p_value_thresh=p_value_thresh,
        num_permutations=num_permutations,
    )

    if job_id:
        update_job(job_id, stage="building_signatures", progress=0.4)
    event_bus.publish_sync(ForensicEvent(type="correlate_stage", data={"stage": "building_signatures", "progress": 0.4}))

    summary, attributions = engine.run()

    if job_id:
        update_job(job_id, stage="running_permutation_test", progress=0.7)
    event_bus.publish_sync(ForensicEvent(type="correlate_stage", data={"stage": "running_permutation_test", "progress": 0.7}))

    resp: dict[str, Any] = {
        "status": "completed",
        "summary": summary.to_dict(),
    }

    if job_id:
        update_job(job_id, stage="persisting_results", progress=0.9)
    event_bus.publish_sync(ForensicEvent(type="correlate_stage", data={"stage": "persisting_results", "progress": 0.9}))

    # Broadcast event to live WebSocket clients
    event_bus.publish_sync(
        ForensicEvent(
            type="correlation_updated",
            data={
                "attributions_count": len(attributions),
                "timestamp": time.time(),
            },
        )
    )

    # Evaluate against ground truth if registered or given path
    gt_file: Path | None = None
    if ground_truth_path:
        p = Path(ground_truth_path)
        if p.exists():
            gt_file = p
    if not gt_file:
        try:
            gt_file = resolve_registered_ground_truth(dataset_name)
        except Exception as err:
            logger.debug("Failed resolving dataset ground truth %s: %s", dataset_name, err)
            gt_file = None

    if gt_file and gt_file.exists():
        aem_res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
        aem_map = dict(aem_res)
        resp["eval_metrics"] = CorrelateEvaluator.evaluate_attribution(
            attributions=attributions,
            ground_truth_path=gt_file,
            address_entity_map=aem_map,
        )

    return resp


@router.post("/run")
def trigger_correlation(request: Request, req: CorrelateRunRequest = CorrelateRunRequest()) -> Any:
    """Run full network-blockchain correlation engine and persist results."""
    is_async = (
        req.async_mode
        or request.query_params.get("async") == "true"
        or request.query_params.get("async_mode") == "true"
        or request.headers.get("prefer") == "respond-async"
    )

    if is_async:
        req_dict = req.dict()
        job = create_and_start_job("correlation", _execute_correlate_sync, req_dict)
        return JSONResponse(status_code=202, content={"job_id": job.job_id, "status": "started"})

    return _execute_correlate_sync(req.dict())



@router.get("/entity/{entity_id}")
def get_entity_attribution(
    entity_id: str,
    limit: int = Query(5, ge=1, le=20),
) -> list[dict[str, Any]]:
    """Retrieve top candidate origin IPs for an entity with posterior scores."""
    db = get_db()
    return db.get_entity_ip_attribution(entity_id=entity_id, limit=limit)


@router.get("/operator-links")
def list_operator_links(
    limit: int = Query(50, ge=1, le=200),
    max_p_value: float = Query(0.05, ge=0.0, le=1.0),
) -> list[dict[str, Any]]:
    """Retrieve statistically significant shares_origin multi-cluster links."""
    db = get_db()
    return db.list_shares_origin_links(limit=limit, max_p_value=max_p_value)


@router.get("/signatures/{entity_id}")
def get_entity_signature(entity_id: str) -> dict[str, Any]:
    """Retrieve behavioral network signatures (ports, churn, circadian entropy) for an entity."""
    db = get_db()
    try:
        sig = db.get_entity_network_signatures(entity_id)
    except Exception as err:
        logger.warning("Error fetching signature for entity %s: %s", entity_id, err)
        raise HTTPException(status_code=404, detail=f"No network signatures for entity {entity_id}")
    if not sig:
        raise HTTPException(status_code=404, detail=f"No network signatures for entity {entity_id}")
    return sig


@router.get("/metrics")
def get_correlation_metrics(
    dataset_name: str | None = Query(None, description="Server-registered dataset name"),
) -> dict[str, Any]:
    """Compute IP attribution accuracy benchmarks against ground truth."""
    db = get_db()

    # Resolve server-side only — no raw filesystem paths accepted
    gt_file: Path | None = None
    try:
        gt_file = resolve_registered_ground_truth(dataset_name)
    except Exception as err:
        logger.debug("Failed resolving dataset ground truth %s: %s", dataset_name, err)
        gt_file = None

    if not gt_file:
        for candidate in [
            settings.DATA_DIR / "cli_test" / "ground_truth.json",
            settings.DATA_DIR / "samples" / "ground_truth.json",
        ]:
            if candidate.exists():
                gt_file = candidate
                break

    if not gt_file or not gt_file.exists():
        raise HTTPException(status_code=404, detail="Ground truth file not found")

    # Load attributions from DB
    links_cursor = db.conn.execute("SELECT entity_id, ip, score, posterior_prob, n_tx, first_seen_ratio FROM ip_entity_links ORDER BY posterior_prob DESC")
    attributions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cols = [desc[0] for desc in links_cursor.description]
    for row in links_cursor.fetchall():
        d = dict(zip(cols, row))
        attributions[d["entity_id"]].append(d)

    aem_res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
    aem_map = dict(aem_res)

    return CorrelateEvaluator.evaluate_attribution(
        attributions=dict(attributions),
        ground_truth_path=gt_file,
        address_entity_map=aem_map,
    )
