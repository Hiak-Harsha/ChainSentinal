"""FastAPI router for dataset ingestion, schema mapping, and QC reports."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
import json
from pathlib import Path
import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.core.config import settings
from chainsentinel.ingest.pipeline import IngestPipeline, detect_parser
from chainsentinel.ingest.schema_mapper import SchemaMapper
from chainsentinel.storage.db import DatabaseManager

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

# Shared in-memory state for active jobs and progress channels
_active_progress: dict[str, dict[str, Any]] = {}
_progress_events: dict[str, asyncio.Queue] = {}


class SchemaDetectRequest(BaseModel):
    file_path: str


class SaveProfileRequest(BaseModel):
    profile_name: str
    mapping: dict[str, str]


class IngestJobStartRequest(BaseModel):
    file_path: str
    format: str | None = None
    profile_name: str | None = None


def _get_db() -> DatabaseManager:
    return DatabaseManager(db_path=settings.DB_PATH)


@router.post("/detect-schema")
async def detect_schema(
    request: Request,
) -> dict[str, Any]:
    """Inspect headers and sample rows to auto-detect canonical schema mapping."""
    content_type = request.headers.get("content-type", "")
    target_path: Path | None = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_file = form.get("file")
        if not uploaded_file:
            raise HTTPException(status_code=400, detail="No file provided in form-data")
        upload_dir = settings.DATA_DIR / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = getattr(uploaded_file, "filename", "uploaded_file")
        temp_path = upload_dir / f"preview_{int(time.time()*1000)}_{filename}"
        content = await uploaded_file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        target_path = temp_path
    else:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Must provide either multipart file upload or JSON payload with file_path")
        file_path_str = body.get("file_path") if isinstance(body, dict) else None
        if not file_path_str:
            raise HTTPException(status_code=400, detail="Must provide file_path in JSON body")
        target_path = Path(file_path_str)
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="File path not found")

    try:
        parser = detect_parser(target_path)
        headers = parser.get_headers()
        sample = parser.get_sample(n=5)
        mapper = SchemaMapper.auto_detect(headers)
        return {
            "file_name": target_path.name,
            "headers": headers,
            "sample_rows": sample,
            "detected_mapping": mapper.mapping,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect file schema: {str(e)}")


@router.post("/save-profile")
async def save_profile(req: SaveProfileRequest) -> dict[str, Any]:
    """Save a schema mapping profile for future re-use."""
    db = _get_db()
    db.save_schema_profile(req.profile_name, req.mapping, created_at=time.time())
    return {"status": "ok", "profile_name": req.profile_name}


@router.get("/profiles")
async def list_profiles() -> list[dict[str, Any]]:
    """List all saved schema mapping profiles."""
    db = _get_db()
    return db.list_schema_profiles()


def _run_ingest_task(
    job_id: str,
    file_path: Path,
    format_hint: str | None,
    mapping_override: dict[str, str] | None,
) -> None:
    """Synchronous worker function running inside background tasks."""
    db = _get_db()
    pipeline = IngestPipeline(db=db)

    def on_progress(pinfo: dict[str, Any]) -> None:
        _active_progress[job_id] = pinfo
        if job_id in _progress_events:
            try:
                _progress_events[job_id].put_nowait(pinfo)
            except Exception:
                pass

    try:
        rep = pipeline.run(
            file_path=file_path,
            format_hint=format_hint,
            mapping_override=mapping_override,
            job_id=job_id,
            progress_callback=on_progress,
        )
        final_info = {
            "job_id": job_id,
            "status": "completed",
            "processed": rep.total_rows_processed,
            "valid": rep.valid_rows,
            "quarantined": rep.quarantined_rows,
            "qc_report": rep.to_dict(),
        }
        _active_progress[job_id] = final_info
        if job_id in _progress_events:
            _progress_events[job_id].put_nowait(final_info)
    except Exception as e:
        error_info = {"job_id": job_id, "status": "failed", "error": str(e)}
        _active_progress[job_id] = error_info
        if job_id in _progress_events:
            _progress_events[job_id].put_nowait(error_info)


@router.post("/upload")
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    profile_name: str | None = Query(None),
) -> dict[str, Any]:
    """Upload a dataset file and start asynchronous ingestion."""
    upload_dir = settings.DATA_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    job_id = f"job_{int(time.time() * 1000)}"
    dest_path = upload_dir / f"{job_id}_{file.filename}"

    with open(dest_path, "wb") as f:
        content = await file.read()
        f.write(content)

    db = _get_db()
    mapping_override = None
    if profile_name:
        mapping_override = db.get_schema_profile(profile_name)

    _active_progress[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "processed": 0,
        "valid": 0,
        "quarantined": 0,
    }
    _progress_events[job_id] = asyncio.Queue()

    background_tasks.add_task(
        _run_ingest_task,
        job_id=job_id,
        file_path=dest_path,
        format_hint=dest_path.suffix.lstrip("."),
        mapping_override=mapping_override,
    )

    return {
        "job_id": job_id,
        "file_name": file.filename,
        "status": "started",
        "progress_url": f"/api/ingest/progress/{job_id}",
    }


@router.get("/jobs")
async def list_jobs() -> list[dict[str, Any]]:
    """List recent ingestion jobs."""
    db = _get_db()
    return db.list_ingest_jobs()


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    """Get status and statistics for an ingestion job."""
    db = _get_db()
    job = db.get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return job


@router.get("/jobs/{job_id}/qc-report")
async def get_qc_report(job_id: str) -> dict[str, Any]:
    """Retrieve full Data-Quality Report for an ingestion job."""
    db = _get_db()
    job = db.get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    report = job.get("qc_report")
    if not report:
        raise HTTPException(status_code=404, detail="QC report not available for this job")
    return report


@router.get("/progress/{job_id}")
async def stream_progress(job_id: str) -> EventSourceResponse:
    """Stream Server-Sent Events (SSE) for live ingestion job progress."""
    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        q = _progress_events.get(job_id)
        if not q:
            # Check current status
            curr = _active_progress.get(job_id)
            if curr:
                yield {"event": "progress", "data": json.dumps(curr)}
            return

        while True:
            try:
                data = await asyncio.wait_for(q.get(), timeout=20.0)
                yield {"event": "progress", "data": json.dumps(data)}
                if data.get("status") in ("completed", "failed"):
                    break
            except asyncio.TimeoutError:
                # Keep-alive heartbeat
                yield {"event": "ping", "data": "keep-alive"}

    return EventSourceResponse(event_generator())
