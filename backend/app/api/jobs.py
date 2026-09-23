"""Background job registry and management router for long-running forensic operations."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import APIRouter, HTTPException

from app.core.events import ForensicEvent, event_bus

logger = logging.getLogger("chainsentinel.api.jobs")
router = APIRouter(prefix="/jobs", tags=["Background Jobs"])


@dataclass
class JobState:
    job_id: str
    job_type: str
    status: str  # "started", "running", "completed", "failed"
    progress: float = 0.0  # 0.0 to 1.0
    stage: str = "initialized"
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


_jobs: dict[str, JobState] = {}
_jobs_lock = threading.Lock()


def get_job(job_id: str) -> JobState | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def update_job(
    job_id: str,
    status: str | None = None,
    progress: float | None = None,
    stage: str | None = None,
    result: Any = None,
    error: str | None = None,
) -> JobState | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if stage is not None:
            job.stage = stage
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        job.updated_at = time.time()

        # Emit websocket event for progress
        event_bus.publish_sync(
            ForensicEvent(
                type="job_progress",
                data={
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "status": job.status,
                    "progress": job.progress,
                    "stage": job.stage,
                },
            )
        )
        return job


def create_and_start_job(
    job_type: str,
    target_func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> JobState:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = JobState(job_id=job_id, job_type=job_type, status="started")
    with _jobs_lock:
        _jobs[job_id] = job

    def _worker():
        try:
            update_job(job_id, status="running", stage="running", progress=0.1)
            res = target_func(*args, **kwargs)
            update_job(job_id, status="completed", stage="completed", progress=1.0, result=res)
        except Exception as e:
            logger.exception("Background job %s failed: %s", job_id, e)
            update_job(job_id, status="failed", stage="failed", error=str(e))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return job


@router.get("/{job_id}")
def get_job_status(job_id: str) -> dict[str, Any]:
    """Poll status and result of a background job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job.to_dict()


@router.get("")
def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    """List recent background jobs."""
    with _jobs_lock:
        jobs_list = sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)[:limit]
        return [j.to_dict() for j in jobs_list]
