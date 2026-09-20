"""FastAPI router for blockchain entity resolution and forensic graph analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from chainsentinel.eval.cluster_eval import ClusterEvaluator
from chainsentinel.graph.entity_resolver import EntityResolver
from chainsentinel.storage.db import DatabaseManager

router = APIRouter(prefix="/graph", tags=["Graph & Entity Resolution"])


class ClusterRequest(BaseModel):
    change_threshold: float = 0.75
    min_coinjoin_outputs: int = 3
    ground_truth_path: str | None = None


def _get_db() -> DatabaseManager:
    return DatabaseManager(db_path=settings.DB_PATH)


@router.post("/cluster")
def trigger_clustering(req: ClusterRequest = ClusterRequest()) -> dict[str, Any]:
    """Run entity resolution (CIOH + CoinJoin exclusion + change heuristics) and build graph."""
    db = _get_db()
    resolver = EntityResolver(
        db=db,
        change_threshold=req.change_threshold,
        min_coinjoin_outputs=req.min_coinjoin_outputs,
    )
    summary, _ = resolver.run()
    resp = {
        "status": "completed",
        "summary": summary.to_dict(),
    }

    # If ground truth path provided or default exists, calculate evaluation metrics
    gt_file = Path(req.ground_truth_path) if req.ground_truth_path else None
    if not gt_file and (settings.DATA_DIR / "cli_test" / "ground_truth.json").exists():
        gt_file = settings.DATA_DIR / "cli_test" / "ground_truth.json"

    if gt_file and gt_file.exists():
        gt_map = ClusterEvaluator.load_ground_truth_map(gt_file)
        # Fetch discovered map from DB
        res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
        disc_map = dict(res)
        resp["eval_metrics"] = ClusterEvaluator.evaluate(disc_map, gt_map)

    return resp


@router.get("/entities")
def list_entities(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    entity_type: str | None = Query(None),
) -> list[dict[str, Any]]:
    """List resolved entities sorted by address count and transaction volume."""
    db = _get_db()
    return db.list_entities(limit=limit, offset=offset, entity_type=entity_type)


@router.get("/entities/{entity_id}")
def get_entity_detail(entity_id: str) -> dict[str, Any]:
    """Retrieve details, metrics, and member addresses of an entity."""
    db = _get_db()
    ent = db.get_entity(entity_id)
    if not ent:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    addresses = db.get_entity_addresses(entity_id, limit=100)
    ent["addresses"] = addresses
    return ent


@router.get("/subgraph")
def get_subgraph(
    center_id: str = Query(..., description="Entity ID, TXID, or Bitcoin address"),
    hops: int = Query(2, ge=1, le=4),
    max_edges: int = Query(150, ge=10, le=500),
) -> dict[str, Any]:
    """Extract an ego subgraph around center_id formatted for Cytoscape.js or D3.js."""
    db = _get_db()
    return db.get_ego_subgraph(center_id=center_id, hops=hops, max_edges=max_edges)


@router.get("/metrics")
def get_evaluation_metrics(
    ground_truth_path: str | None = Query(None),
) -> dict[str, Any]:
    """Compute clustering accuracy (ARI, NMI, Precision, Recall) against ground truth."""
    db = _get_db()
    gt_file = Path(ground_truth_path) if ground_truth_path else None
    if not gt_file and (settings.DATA_DIR / "cli_test" / "ground_truth.json").exists():
        gt_file = settings.DATA_DIR / "cli_test" / "ground_truth.json"

    if not gt_file or not gt_file.exists():
        raise HTTPException(status_code=404, detail="Ground truth file not found")

    gt_map = ClusterEvaluator.load_ground_truth_map(gt_file)
    res = db.conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
    disc_map = dict(res)
    return ClusterEvaluator.evaluate(disc_map, gt_map)
