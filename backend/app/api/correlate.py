"""FastAPI router for Network-Blockchain Correlation Engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from chainsentinel.correlate.engine import CorrelationEngine
from chainsentinel.eval.correlate_eval import CorrelateEvaluator
from chainsentinel.storage.db import DatabaseManager

router = APIRouter(prefix="/correlate", tags=["Network Correlation"])


from chainsentinel.common.datasets import resolve_registered_ground_truth


class CorrelateRunRequest(BaseModel):
    time_window_sec: float = 60.0
    p_value_thresh: float = 0.05
    num_permutations: int = 100
    dataset_name: str | None = None


def _get_db() -> DatabaseManager:
    return DatabaseManager(db_path=settings.DB_PATH)


@router.post("/run")
def trigger_correlation(req: CorrelateRunRequest = CorrelateRunRequest()) -> dict[str, Any]:
    """Run full network-blockchain correlation engine and persist results."""
    db = _get_db()
    engine = CorrelationEngine(
        db=db,
        time_window_sec=req.time_window_sec,
        p_value_thresh=req.p_value_thresh,
        num_permutations=req.num_permutations,
    )
    summary, attributions = engine.run()

    resp: dict[str, Any] = {
        "status": "completed",
        "summary": summary.to_dict(),
    }

    # Evaluate against ground truth if registered
    gt_file: Path | None = None
    try:
        gt_file = resolve_registered_ground_truth(req.dataset_name)
    except Exception:
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


@router.get("/entity/{entity_id}")
def get_entity_attribution(
    entity_id: str,
    limit: int = Query(5, ge=1, le=20),
) -> list[dict[str, Any]]:
    """Retrieve top candidate origin IPs for an entity with posterior scores."""
    db = _get_db()
    return db.get_entity_ip_attribution(entity_id=entity_id, limit=limit)


@router.get("/operator-links")
def list_operator_links(
    limit: int = Query(50, ge=1, le=200),
    max_p_value: float = Query(0.05, ge=0.0, le=1.0),
) -> list[dict[str, Any]]:
    """Retrieve statistically significant shares_origin multi-cluster links."""
    db = _get_db()
    return db.list_shares_origin_links(limit=limit, max_p_value=max_p_value)


@router.get("/signatures/{entity_id}")
def get_entity_signature(entity_id: str) -> dict[str, Any]:
    """Retrieve behavioral network signatures (ports, churn, circadian entropy) for an entity."""
    db = _get_db()
    sig = db.get_entity_network_signatures(entity_id)
    if not sig:
        raise HTTPException(status_code=404, detail=f"No network signatures for entity {entity_id}")
    return sig


@router.get("/metrics")
def get_correlation_metrics(
    ground_truth_path: str | None = Query(None),
) -> dict[str, Any]:
    """Compute IP attribution accuracy benchmarks against ground truth."""
    db = _get_db()
    gt_file = Path(ground_truth_path) if ground_truth_path else None
    if not gt_file and (settings.DATA_DIR / "cli_test" / "ground_truth.json").exists():
        gt_file = settings.DATA_DIR / "cli_test" / "ground_truth.json"

    if not gt_file or not gt_file.exists():
        raise HTTPException(status_code=404, detail="Ground truth file not found")

    # Load attributions from DB
    links_cursor = db.conn.execute("SELECT entity_id, ip, score, posterior_prob, n_tx, first_seen_ratio FROM ip_entity_links ORDER BY posterior_prob DESC")
    from collections import defaultdict
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
