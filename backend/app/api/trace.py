"""Forensic tracing, pathfinding, and autonomous investigation REST endpoints."""

from __future__ import annotations

import csv
import html
import io
import logging
import time
from typing import Any
import uuid

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.db_singleton import get_db
from app.core.events import ForensicEvent, event_bus
from chainsentinel.evidence import verify_bundle_integrity
from chainsentinel.storage.db import DatabaseManager
from chainsentinel.trace.agent import AutonomousInvestigator
from chainsentinel.trace.pathfinder import InvestigativePathfinder
from chainsentinel.trace.taint_tracker import TaintTracker

logger = logging.getLogger("chainsentinel.api.trace")
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


class CaseTimelineEventRequest(BaseModel):
    event_type: str = Field(..., description="Event classification, e.g. entity_viewed, trace_run, note_added")
    target_id: str = Field(..., description="Target entity ID, address, or TXID")
    details: dict[str, Any] = Field(default_factory=dict, description="Event metadata payload")


@router.post("/run")
def run_trace(request: Request, req: TraceRequest) -> dict[str, Any]:
    """Execute dynamic taint tracking run (Forward, Backward, or Both)."""
    db = get_db()
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
        logger.error("Trace execution failed for target %s: %s", req.target, e)
        raise HTTPException(status_code=500, detail=f"Trace execution failed: {str(e)}")


@router.get("/history")
def list_traces(limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    """List historical taint trace runs."""
    db = get_db()
    return db.list_taint_traces(limit=limit)


@router.get("/cases")
def list_cases(limit: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    """List forensic investigative case files."""
    db = get_db()
    return db.list_investigative_cases(limit=limit)


@router.get("/cases/{case_id}")
def get_case_file(case_id: str) -> dict[str, Any]:
    """Retrieve full investigative case file including evidence bundle and Cytoscape graph."""
    db = get_db()
    try:
        case = db.get_investigative_case(case_id)
    except Exception as err:
        logger.warning("Error fetching case %s: %s", case_id, err)
        raise HTTPException(status_code=404, detail=f"Investigative case '{case_id}' not found")
    if not case:
        raise HTTPException(status_code=404, detail=f"Investigative case '{case_id}' not found")
    return case.get("case_data", case)


@router.get("/cases/{case_id}/timeline")
def get_case_timeline_route(case_id: str) -> list[dict[str, Any]]:
    """Retrieve chronological investigation events for a case."""
    db = get_db()
    return db.get_case_timeline(case_id)


@router.post("/cases/{case_id}/timeline")
def add_case_timeline_event_route(case_id: str, req: CaseTimelineEventRequest) -> dict[str, Any]:
    """Record a user action / investigative pivot into the case timeline."""
    db = get_db()
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    ts = time.time()
    db.record_case_timeline_event(
        event_id=event_id,
        case_id=case_id,
        event_type=req.event_type,
        target_id=req.target_id,
        details=req.details,
        timestamp=ts,
    )
    return {
        "event_id": event_id,
        "case_id": case_id,
        "status": "recorded",
        "timestamp": ts,
    }


@router.get("/cases/{case_id}/export/html")
def export_case_dossier_html(case_id: str) -> Response:
    """Export forensic case dossier as a self-contained, printable court-admissible HTML report."""
    db = get_db()
    case_row = db.get_investigative_case(case_id)
    if not case_row:
        raise HTTPException(status_code=404, detail=f"Case file '{case_id}' not found")

    case_data = case_row.get("case_data", case_row)
    html_content = _render_case_dossier_html(case_data)
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Content-Disposition": f'inline; filename="{case_id}_dossier.html"',
        },
    )


@router.get("/cases/{case_id}/export/csv")
def export_case_hops_csv(case_id: str) -> Response:
    """Export trace hops from a case dossier as structured CSV."""
    db = get_db()
    case_row = db.get_investigative_case(case_id)
    if not case_row:
        raise HTTPException(status_code=404, detail=f"Case file '{case_id}' not found")

    case_data = case_row.get("case_data", case_row)
    csv_content = _render_case_hops_csv(case_data)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{case_id}_hops.csv"',
        },
    )


@router.get("/cases/{case_id}/export")
def export_case_dossier_generic(case_id: str, format: str = Query("html", pattern="^(html|csv)$")) -> Response:
    """Generic export dispatcher for case dossiers supporting format=html or format=csv."""
    if format.lower() == "csv":
        return export_case_hops_csv(case_id)
    return export_case_dossier_html(case_id)


@router.get("/{trace_id}")
def get_trace(trace_id: str) -> dict[str, Any]:
    """Fetch completed taint trace by trace_id."""
    db = get_db()
    try:
        trace = db.get_taint_trace(trace_id)
    except Exception as err:
        logger.warning("Error fetching taint trace %s: %s", trace_id, err)
        raise HTTPException(status_code=404, detail=f"Taint trace '{trace_id}' not found")
    if not trace:
        raise HTTPException(status_code=404, detail=f"Taint trace '{trace_id}' not found")
    return trace


@router.post("/path")
def compute_path(req: PathRequest) -> dict[str, Any]:
    """Compute forensic paths between two entities (shortest or highest-volume bottleneck)."""
    db = get_db()
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
    db = get_db()
    agent = AutonomousInvestigator(db)
    try:
        case = agent.investigate(
            target=req.target,
            max_hops=req.max_hops,
            decay_model=req.decay_model,
            title=req.title,
        )
        # Log case created timeline event
        case_id = case.get("case_id", "")
        if case_id:
            db.record_case_timeline_event(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                case_id=case_id,
                event_type="investigation_initiated",
                target_id=req.target,
                details={"max_hops": req.max_hops, "decay_model": req.decay_model},
            )
            event_bus.publish_sync(
                ForensicEvent(
                    type="case_updated",
                    data={"case_id": case_id, "target_id": req.target, "title": case.get("title")},
                )
            )
        return case
    except Exception as e:
        logger.error("Investigation failed for target %s: %s", req.target, e)
        raise HTTPException(status_code=500, detail=f"Investigation failed: {str(e)}")


def _render_case_hops_csv(case: dict[str, Any]) -> str:
    """Render hops from a case file into structured CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "case_id",
        "direction",
        "hop_index",
        "source_entity",
        "target_entity",
        "tainted_satoshis",
        "taint_pct",
        "target_type",
        "stop_reason",
    ])

    case_id = case.get("case_id", "UNKNOWN")
    bundle = case.get("evidence_bundle", {})

    # Extract hops from graph elements
    subgraph = case.get("cytoscape_subgraph", bundle.get("cytoscape_subgraph", {}))
    elements = subgraph.get("elements", {})
    edges = elements.get("edges", [])

    for i, edge in enumerate(edges, start=1):
        edata = edge.get("data", {})
        writer.writerow([
            case_id,
            edata.get("direction", "forward"),
            edata.get("hop_index", i),
            edata.get("source", ""),
            edata.get("target", ""),
            edata.get("amount", edata.get("tainted_sat", 0)),
            edata.get("taint_ratio", edata.get("taint_pct", 0)),
            edata.get("target_type", "UNKNOWN"),
            edata.get("stop_reason", ""),
        ])

    return output.getvalue()


def _render_case_dossier_html(case: dict[str, Any]) -> str:
    """Render a standalone, print-ready HTML forensic case dossier."""
    case_id = html.escape(str(case.get("case_id", "UNKNOWN")))
    target_id = html.escape(str(case.get("target_id", "UNKNOWN")))
    title = html.escape(str(case.get("title", f"Forensic Case File: {case_id}")))
    bundle_hash = html.escape(str(case.get("bundle_hash", "UNSIGNED")))
    created_ts = case.get("created_at", int(time.time()))
    created_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(created_ts))

    bundle = case.get("evidence_bundle", {})
    target_meta = bundle.get("target_metadata", {})
    network_intel = bundle.get("network_intelligence", {})
    subgraph = case.get("cytoscape_subgraph", bundle.get("cytoscape_subgraph", {}))
    edges = subgraph.get("elements", {}).get("edges", [])

    entity_type = html.escape(str(target_meta.get("entity_type", "UNKNOWN")))
    risk_score = float(target_meta.get("risk_score", 0.0))
    address_count = target_meta.get("address_count", 0)
    inflow_sat = target_meta.get("total_in_sat", 0)
    outflow_sat = target_meta.get("total_out_sat", 0)

    # Check seal integrity
    is_valid = verify_bundle_integrity(bundle, expected_hash=case.get("bundle_hash"))

    # Attributed IPs
    ips_html = ""
    for item in network_intel.get("attributed_ips", []):
        ip_val = html.escape(str(item.get("ip", "")))
        score_val = f"{float(item.get('score', 0.0)):.2f}"
        prob_val = f"{float(item.get('posterior_prob', 0.0))*100:.1f}%"
        tx_val = item.get("tx_count", 0)
        ips_html += f"<tr><td><code>{ip_val}</code></td><td>{score_val}</td><td>{prob_val}</td><td>{tx_val}</td></tr>"
    if not ips_html:
        ips_html = "<tr><td colspan='4' class='text-muted'>No network broadcast IPs attributed with confidence &ge; 0.50.</td></tr>"

    # Hops table
    hops_html = ""
    for i, edge in enumerate(edges, start=1):
        edata = edge.get("data", {})
        src = html.escape(str(edata.get("source", "")))
        dst = html.escape(str(edata.get("target", "")))
        dir_val = html.escape(str(edata.get("direction", "forward"))).upper()
        amt = edata.get("amount", edata.get("tainted_sat", 0))
        pct = edata.get("taint_ratio", edata.get("taint_pct", 0))
        pct_str = f"{pct*100:.1f}%" if isinstance(pct, float) and pct <= 1.0 else f"{pct}%"
        ttype = html.escape(str(edata.get("target_type", "UNKNOWN")))
        stop = html.escape(str(edata.get("stop_reason", "—")))

        hops_html += (
            f"<tr>"
            f"<td>{i}</td>"
            f"<td><span class='badge badge-dir'>{dir_val}</span></td>"
            f"<td><code>{src}</code></td>"
            f"<td><code>{dst}</code></td>"
            f"<td>{amt:,.0f} sat</td>"
            f"<td>{pct_str}</td>"
            f"<td>{ttype}</td>"
            f"<td>{stop}</td>"
            f"</tr>"
        )
    if not hops_html:
        hops_html = "<tr><td colspan='8' class='text-muted'>No multi-hop taint movements recorded.</td></tr>"

    # Narrative lines
    narrative_lines = case.get("narrative_report", "").split("\n")
    narrative_html = "".join(f"<p>{html.escape(l)}</p>" for l in narrative_lines if l.strip())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ChainSentinel Case Dossier — {case_id}</title>
<style>
  :root {{
    --bg: #090d16;
    --card: #111827;
    --border: #1f293d;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --accent: #f59e0b;
    --cyan: #06b6d4;
    --green: #10b981;
    --red: #ef4444;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    padding: 32px;
  }}
  .container {{
    max-width: 960px;
    margin: 0 auto;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 32px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 2px solid var(--border);
    padding-bottom: 20px;
    margin-bottom: 24px;
  }}
  .title-block h1 {{
    font-size: 22px;
    color: #fff;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }}
  .subhead {{
    color: var(--cyan);
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .seal-badge {{
    text-align: right;
  }}
  .seal-stamp {{
    display: inline-block;
    background: rgba(16, 185, 129, 0.1);
    color: var(--green);
    border: 1px solid var(--green);
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
  }}
  .hash-box {{
    margin-top: 6px;
    font-family: monospace;
    font-size: 11px;
    color: var(--text-muted);
    word-break: break-all;
    max-width: 320px;
  }}
  .actions-bar {{
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-bottom: 20px;
  }}
  .btn {{
    background: var(--border);
    color: #fff;
    border: 1px solid #334155;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
  }}
  .btn:hover {{ background: #334155; }}
  .btn-print {{ background: #2563eb; border-color: #3b82f6; }}
  .btn-print:hover {{ background: #1d4ed8; }}
  .grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
  }}
  .meta-card {{
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 16px;
  }}
  .meta-row {{
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }}
  .meta-row:last-child {{ border-bottom: none; }}
  .meta-label {{ color: var(--text-muted); font-size: 12px; }}
  .meta-value {{ font-weight: 600; font-size: 13px; }}
  code {{
    font-family: "SFMono-Regular", Consolas, Menlo, monospace;
    background: rgba(0,0,0,0.3);
    padding: 2px 6px;
    border-radius: 3px;
    color: #38bdf8;
    font-size: 12px;
  }}
  h2 {{
    font-size: 16px;
    color: #fff;
    margin: 24px 0 12px 0;
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
    letter-spacing: 0.3px;
  }}
  .narrative {{
    background: rgba(15, 23, 42, 0.4);
    border-left: 3px solid var(--cyan);
    padding: 16px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 24px;
    font-size: 13px;
  }}
  .narrative p {{ margin-bottom: 10px; }}
  .narrative p:last-child {{ margin-bottom: 0; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
    font-size: 12px;
  }}
  th {{
    background: #1e293b;
    color: var(--text-muted);
    text-align: left;
    padding: 8px 12px;
    font-weight: 600;
    border-bottom: 1px solid var(--border);
  }}
  td {{
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }}
  .badge {{
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
  }}
  .badge-dir {{ background: rgba(56, 189, 248, 0.2); color: #38bdf8; }}
  .footer {{
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--text-muted);
    display: flex;
    justify-content: space-between;
  }}
  @media print {{
    body {{ background: #fff !important; color: #000 !important; padding: 0 !important; }}
    .container {{ max-width: 100% !important; box-shadow: none !important; border: none !important; padding: 0 !important; }}
    .actions-bar {{ display: none !important; }}
    .subhead {{ color: #0284c7 !important; }}
    .seal-stamp {{ color: #059669 !important; border-color: #059669 !important; background: transparent !important; }}
    .meta-card, .narrative {{ background: #f8fafc !important; border: 1px solid #cbd5e1 !important; color: #000 !important; }}
    th {{ background: #f1f5f9 !important; color: #334155 !important; border-bottom: 1px solid #cbd5e1 !important; }}
    td {{ border-bottom: 1px solid #e2e8f0 !important; color: #000 !important; }}
    code {{ color: #0f172a !important; background: #e2e8f0 !important; }}
    h1, h2 {{ color: #0f172a !important; }}
    .footer {{ color: #64748b !important; border-top-color: #cbd5e1 !important; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="actions-bar">
    <button class="btn btn-print" onclick="window.print()">Print Dossier / Export to PDF</button>
    <a class="btn" href="/api/trace/cases/{case_id}/export/csv">Export Hops CSV</a>
  </div>

  <div class="header">
    <div class="title-block">
      <div class="subhead">National Technical Research Organisation (NTRO SIH26146)</div>
      <h1>ChainSentinel Case Dossier</h1>
      <div style="color: var(--text-muted); font-size: 12px;">Case Title: {title}</div>
    </div>
    <div class="seal-badge">
      <span class="seal-stamp">{'VERIFIED SHA-256 SEAL' if is_valid else 'SEAL INTEGRITY ERROR'}</span>
      <div class="hash-box">DIGEST: {bundle_hash}</div>
    </div>
  </div>

  <div class="grid-2">
    <div class="meta-card">
      <div class="meta-row"><span class="meta-label">Case Identifier</span><span class="meta-value"><code>{case_id}</code></span></div>
      <div class="meta-row"><span class="meta-label">Subject Target</span><span class="meta-value"><code>{target_id}</code></span></div>
      <div class="meta-row"><span class="meta-label">Classification</span><span class="meta-value">{entity_type}</span></div>
      <div class="meta-row"><span class="meta-label">Risk Severity</span><span class="meta-value" style="color: {'var(--red)' if risk_score >= 0.7 else 'var(--accent)'};">{risk_score:.2f}</span></div>
    </div>
    <div class="meta-card">
      <div class="meta-row"><span class="meta-label">Generation Time</span><span class="meta-value">{created_str}</span></div>
      <div class="meta-row"><span class="meta-label">Monitored Addresses</span><span class="meta-value">{address_count:,}</span></div>
      <div class="meta-row"><span class="meta-label">Historical Inflow</span><span class="meta-value">{inflow_sat:,} sat</span></div>
      <div class="meta-row"><span class="meta-label">Historical Outflow</span><span class="meta-value">{outflow_sat:,} sat</span></div>
    </div>
  </div>

  <h2>1. Investigative Narrative & Chain-of-Custody Summary</h2>
  <div class="narrative">
    {narrative_html}
  </div>

  <h2>2. Operator Network Attribution & Infrastructure Intelligence</h2>
  <table>
    <thead>
      <tr><th>Attributed Broadcast IP</th><th>Attribution Score</th><th>Posterior Probability</th><th>Observed TXs</th></tr>
    </thead>
    <tbody>
      {ips_html}
    </tbody>
  </table>

  <h2>3. Multi-Hop Forensic Taint Flows</h2>
  <table>
    <thead>
      <tr><th>#</th><th>Direction</th><th>Source Entity</th><th>Target Entity</th><th>Tainted Satoshis</th><th>Taint %</th><th>Entity Type</th><th>Halt Reason</th></tr>
    </thead>
    <tbody>
      {hops_html}
    </tbody>
  </table>

  <div class="footer">
    <div>CONFIDENTIAL — FOR DEFENSE AND LAW ENFORCEMENT INVESTIGATORS ONLY</div>
    <div>Generated by ChainSentinel AI Forensic Intelligence Engine (Air-Gapped Edition)</div>
  </div>
</div>
</body>
</html>"""
