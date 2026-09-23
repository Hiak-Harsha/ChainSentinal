"""FastAPI router for blockchain entity resolution and forensic graph analysis."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.db_singleton import get_db
from chainsentinel.eval.cluster_eval import ClusterEvaluator
from chainsentinel.graph.entity_resolver import EntityResolver
from chainsentinel.storage.db import DatabaseManager

logger = logging.getLogger("chainsentinel.api.graph")
router = APIRouter(prefix="/graph", tags=["Graph & Entity Resolution"])


from chainsentinel.common.datasets import resolve_registered_ground_truth


from fastapi.responses import JSONResponse
from app.api.jobs import create_and_start_job, update_job
from app.core.events import ForensicEvent, event_bus


class ClusterRequest(BaseModel):
    change_threshold: float = Field(0.75, ge=0.0, le=1.0, description="Change address confidence threshold")
    min_coinjoin_outputs: int = Field(3, ge=2, le=20, description="Minimum outputs for CoinJoin detection")
    dataset_name: str | None = None
    ground_truth_path: str | None = None
    async_mode: bool = Field(False, description="Run as background job returning 202 Accepted")


def _execute_clustering_sync(req_dict: dict[str, Any], job_id: str | None = None) -> dict[str, Any]:
    db = get_db()
    change_threshold = req_dict.get("change_threshold", 0.75)
    min_coinjoin_outputs = req_dict.get("min_coinjoin_outputs", 3)
    dataset_name = req_dict.get("dataset_name")
    ground_truth_path = req_dict.get("ground_truth_path")

    def _progress(info: dict[str, Any]):
        if job_id:
            update_job(job_id, stage=info.get("stage", "clustering"), progress=info.get("progress", 0.5))
        event_bus.publish_sync(ForensicEvent(type="cluster_merge", data=info))

    resolver = EntityResolver(
        db=db,
        change_threshold=change_threshold,
        min_coinjoin_outputs=min_coinjoin_outputs,
    )
    summary, _ = resolver.run(progress_callback=_progress)
    resp = {
        "status": "completed",
        "summary": summary.to_dict(),
    }

    # Evaluate ground truth if available
    gt_file: Path | None = None
    if ground_truth_path:
        p = Path(ground_truth_path)
        if p.exists():
            gt_file = p
    if not gt_file:
        try:
            gt_file = resolve_registered_ground_truth(dataset_name)
        except Exception:
            gt_file = None

    if gt_file and gt_file.exists():
        gt_map = ClusterEvaluator.load_ground_truth_map(gt_file)
        res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
        disc_map = dict(res)
        resp["eval_metrics"] = ClusterEvaluator.evaluate(disc_map, gt_map)

    # Invalidate similarity cache since entities changed
    from chainsentinel.graph.embeddings import EntitySimilarityEngine
    EntitySimilarityEngine(db).clear_cache()

    return resp


@router.post("/cluster")
def trigger_clustering(request: Request, req: ClusterRequest = ClusterRequest()) -> Any:
    """Run entity resolution (CIOH + CoinJoin exclusion + change heuristics) and build graph."""
    is_async = (
        req.async_mode
        or request.query_params.get("async") == "true"
        or request.query_params.get("async_mode") == "true"
        or request.headers.get("prefer") == "respond-async"
    )

    if is_async:
        req_dict = req.dict()
        job = create_and_start_job("clustering", _execute_clustering_sync, req_dict)
        return JSONResponse(status_code=202, content={"job_id": job.job_id, "status": "started"})

    return _execute_clustering_sync(req.dict())



@router.get("/entities")
def list_entities(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    entity_type: str | None = Query(None),
) -> list[dict[str, Any]]:
    """List resolved entities sorted by address count and transaction volume."""
    db = get_db()
    return db.list_entities(limit=limit, offset=offset, entity_type=entity_type)


@router.get("/entities/{entity_id}")
def get_entity_detail(entity_id: str) -> dict[str, Any]:
    """Retrieve details, metrics, and member addresses of an entity."""
    db = get_db()
    try:
        ent = db.get_entity(entity_id)
    except Exception as err:
        logger.warning("Error fetching entity %s: %s", entity_id, err)
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    if not ent:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    addresses = db.get_entity_addresses(entity_id, limit=100)
    ent["addresses"] = addresses
    return ent


@router.get("/entities/{entity_id}/similar")
def get_similar_entities(
    entity_id: str,
    top_k: int = Query(5, ge=1, le=20, description="Number of structurally similar entities to return"),
) -> list[dict[str, Any]]:
    """Find structurally similar entities based on graph motif topology and network features."""
    from chainsentinel.graph.embeddings import EntitySimilarityEngine
    db = get_db()
    engine = EntitySimilarityEngine(db)
    return engine.find_similar(entity_id=entity_id, top_k=top_k)


@router.get("/subgraph")
def get_subgraph(
    center_id: str = Query(..., description="Entity ID, TXID, or Bitcoin address"),
    hops: int = Query(2, ge=1, le=4),
    max_edges: int = Query(150, ge=10, le=500),
) -> dict[str, Any]:
    """Extract an ego subgraph around center_id formatted for Cytoscape.js or D3.js."""
    db = get_db()
    return db.get_ego_subgraph(center_id=center_id, hops=hops, max_edges=max_edges)


@router.get("/metrics")
def get_evaluation_metrics(
    dataset_name: str | None = Query(None, description="Server-registered dataset name"),
) -> dict[str, Any]:
    """Compute clustering accuracy (ARI, NMI, Precision, Recall) against ground truth."""
    db = get_db()

    # Resolve server-side only — no raw filesystem paths accepted
    gt_file: Path | None = None
    try:
        gt_file = resolve_registered_ground_truth(dataset_name)
    except Exception:
        gt_file = None

    if not gt_file:
        # Fallback to default locations
        for candidate in [
            settings.DATA_DIR / "cli_test" / "ground_truth.json",
            settings.DATA_DIR / "samples" / "ground_truth.json",
        ]:
            if candidate.exists():
                gt_file = candidate
                break

    if not gt_file or not gt_file.exists():
        raise HTTPException(status_code=404, detail="Ground truth file not found")

    gt_map = ClusterEvaluator.load_ground_truth_map(gt_file)
    res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
    disc_map = dict(res)
    return ClusterEvaluator.evaluate(disc_map, gt_map)
