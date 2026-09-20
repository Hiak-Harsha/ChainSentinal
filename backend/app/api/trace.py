"""Forensic tracing, pathfinding, and autonomous investigation REST endpoints."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from chainsentinel.storage.db import DatabaseManager
from chainsentinel.trace.agent import AutonomousInvestigator
from chainsentinel.trace.pathfinder import InvestigativePathfinder
from chainsentinel.trace.taint_tracker import TaintTracker

router = APIRouter(prefix="/trace", tags=["trace"])


class TraceRequest(BaseModel):
    target: str = Field(..., description="Root address, entity ID, or transaction hash")
    direction: str = Field(default="forward", description="forward, backward, or both")
    decay_model: str = Field(default="proportional", description="proportional, fifo, or poison")
    max_hops: int = Field(default=5, ge=1, le=10, description="Max traversal depth")
    amount: int | None = Field(default=None, description="Initial taint in satoshis")
    min_ratio: float = Field(default=0.01, ge=0.0001, le=1.0, description="Pruning threshold")
    stop_at_exchange: bool = Field(default=True, description="Halt path at regulated exchanges")
    stop_at_mixer: bool = Field(default=True, description="Halt path at known mixers")


class PathRequest(BaseModel):
    source: str = Field(..., description="Source entity ID, address, or TXID")
    target: str = Field(..., description="Target entity ID, address, or TXID")
    strategy: str = Field(default="shortest", description="shortest, bottleneck, or all")
    cutoff: int = Field(default=5, ge=1, le=12, description="Max hops for alternative paths")
    limit: int = Field(default=5, ge=1, le=20, description="Max alternative paths to return")


class InvestigateRequest(BaseModel):
    target: str = Field(..., description="Target entity ID, address, or TXID to investigate")
    max_hops: int = Field(default=4, ge=1, le=10, description="Taint tracing horizon")
    decay_model: str = Field(default="proportional", description="proportional, fifo, or poison")
    title: str | None = Field(default=None, description="Custom case title")


@router.post("/run")
def run_trace(request: Request, req: TraceRequest) -> dict[str, Any]:
    """Execute dynamic taint tracking run (Forward, Backward, or Both)."""
    db = DatabaseManager(settings.DB_PATH)
    tracker = TaintTracker(db)
    try:
        res = tracker.trace(
            root_ref=req.target,
            direction=req.direction,
            initial_taint_sat=req.amount,
            max_hops=req.max_hops,
            decay_model=req.decay_model,
            min_taint_ratio=req.min_ratio,
            stop_at_exchange=req.stop_at_exchange,
            stop_at_mixer=req.stop_at_mixer,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trace execution failed: {str(e)}")


@router.get("/history")
def list_traces(limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    """List historical taint trace runs."""
    db = DatabaseManager(settings.DB_PATH)
    return db.list_taint_traces(limit=limit)


@router.get("/cases")
def list_cases(limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    """List forensic investigative case files."""
    db = DatabaseManager(settings.DB_PATH)
    return db.list_investigative_cases(limit=limit)


@router.get("/cases/{case_id}")
def get_case_file(case_id: str) -> dict[str, Any]:
    """Retrieve full investigative case file including evidence bundle and Cytoscape graph."""
    db = DatabaseManager(settings.DB_PATH)
    try:
        case = db.get_investigative_case(case_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Investigative case '{case_id}' not found")
    if not case:
        raise HTTPException(status_code=404, detail=f"Investigative case '{case_id}' not found")
    return case.get("case_data", case)


@router.get("/{trace_id}")
def get_trace(trace_id: str) -> dict[str, Any]:
    """Fetch completed taint trace by trace_id."""
    db = DatabaseManager(settings.DB_PATH)
    try:
        trace = db.get_taint_trace(trace_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Taint trace '{trace_id}' not found")
    if not trace:
        raise HTTPException(status_code=404, detail=f"Taint trace '{trace_id}' not found")
    return trace


@router.post("/path")
def compute_path(req: PathRequest) -> dict[str, Any]:
    """Compute forensic paths between two entities (shortest or highest-volume bottleneck)."""
    db = DatabaseManager(settings.DB_PATH)
    pathfinder = InvestigativePathfinder(db)

    strat = req.strategy.lower()
    if strat in ("bottleneck", "highest_volume"):
        return pathfinder.find_highest_volume_path(source=req.source, target=req.target)
    elif strat in ("all", "candidates"):
        candidates = pathfinder.find_all_candidate_paths(
            source=req.source, target=req.target, cutoff=req.cutoff, limit=req.limit
        )
        return {"source": req.source, "target": req.target, "paths": candidates, "count": len(candidates)}
    else:
        return pathfinder.find_shortest_path(source=req.source, target=req.target)


@router.post("/investigate")
def run_investigation(request: Request, req: InvestigateRequest) -> dict[str, Any]:
    """Launch autonomous investigation on target entity/address/txid."""
    db = DatabaseManager(settings.DB_PATH)
    agent = AutonomousInvestigator(db)
    try:
        case = agent.investigate(
            target=req.target,
            max_hops=req.max_hops,
            decay_model=req.decay_model,
            title=req.title,
        )
        return case
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {str(e)}")
