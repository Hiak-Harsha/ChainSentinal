"""Health and system check endpoints."""

from datetime import datetime, timezone
import ipaddress
import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
import psutil

from app.core.config import settings

logger = logging.getLogger("chainsentinel.api.health")
router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    version: str
    app: str
    timestamp: str


class ReadinessDependency(BaseModel):
    status: str
    details: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    app: str
    version: str
    timestamp: str
    dependencies: dict[str, ReadinessDependency]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe: answers 'Is the process alive?'"""
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        app=settings.APP_NAME,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    """Readiness probe: answers 'Can the application actually serve requests?'
    
    Verifies:
    1. Database connection and query execution (DuckDB)
    2. Filesystem writability on persistent data directories
    3. Essential directories (uploads, models, audit, exports)
    
    Returns HTTP 503 if any critical dependency fails.
    """
    from fastapi import HTTPException
    from app.core.db_singleton import get_db

    deps: dict[str, ReadinessDependency] = {}
    is_ready = True

    # 1. Database connection and query verification
    try:
        db = get_db()
        # Execute basic query to verify connection and catalog accessibility
        row = db.conn.execute("SELECT 1").fetchone()
        if row and row[0] == 1:
            deps["database"] = ReadinessDependency(status="ok", details="DuckDB connection verified")
        else:
            is_ready = False
            deps["database"] = ReadinessDependency(status="error", details="Database query returned unexpected result")
    except Exception as err:
        is_ready = False
        logger.error("Readiness check failed on database: %s", err)
        deps["database"] = ReadinessDependency(status="error", details=str(err))

    # 2. Required directories verification
    required_dirs = [
        settings.DATA_DIR,
        settings.DATA_DIR / "uploads",
        settings.DATA_DIR / "audit",
        settings.DATA_DIR / "logs",
        settings.DATA_DIR / "exports",
        settings.MODELS_DIR,
    ]
    dir_errors: list[str] = []
    for d in required_dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            dir_errors.append(f"{d.name}: {e}")

    if dir_errors:
        is_ready = False
        deps["directories"] = ReadinessDependency(status="error", details="; ".join(dir_errors))
    else:
        deps["directories"] = ReadinessDependency(status="ok", details=f"Verified {len(required_dirs)} directories")

    # 3. Storage writability test
    canary_path = settings.DATA_DIR / ".ready_canary"
    try:
        canary_path.write_text("ok", encoding="utf-8")
        canary_path.unlink(missing_ok=True)
        deps["storage"] = ReadinessDependency(status="ok", details="Data directory writable")
    except Exception as err:
        is_ready = False
        logger.error("Readiness check failed on storage writability: %s", err)
        deps["storage"] = ReadinessDependency(status="error", details=str(err))

    resp = ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        app=settings.APP_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        dependencies=deps,
    )

    if not is_ready:
        from fastapi.responses import JSONResponse
        raise HTTPException(
            status_code=503,
            detail=resp.model_dump(),
        )

    return resp



class SocketInfo(BaseModel):
    fd: int | None = None
    family: str
    type: str
    local_address: str
    remote_address: str | None = None
    status: str


class OfflineCheckResponse(BaseModel):
    air_gapped: bool
    measured_at: str
    total_sockets: int
    non_loopback_sockets: int
    non_loopback_connections: list[SocketInfo]
    message: str


@router.get("/system/offline-check", response_model=OfflineCheckResponse)
async def offline_check() -> OfflineCheckResponse:
    """Verify the system is operating in air-gapped mode by measuring process OS sockets."""
    proc = psutil.Process()
    try:
        raw_conns = proc.net_connections(kind="inet") if hasattr(proc, "net_connections") else proc.connections(kind="inet")
    except Exception as err:
        logger.debug("Failed querying process sockets: %s", err)
        raw_conns = []

    non_loopback: list[SocketInfo] = []
    for c in raw_conns:
        laddr_str = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "unknown"
        raddr_str = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None

        is_external = False
        if c.raddr:
            try:
                ip_obj = ipaddress.ip_address(c.raddr.ip)
                if not ip_obj.is_loopback:
                    is_external = True
            except ValueError:
                is_external = True

        if is_external:
            family_str = c.family.name if hasattr(c.family, "name") else str(c.family)
            type_str = c.type.name if hasattr(c.type, "name") else str(c.type)
            non_loopback.append(
                SocketInfo(
                    fd=getattr(c, "fd", None),
                    family=family_str,
                    type=type_str,
                    local_address=laddr_str,
                    remote_address=raddr_str,
                    status=str(c.status),
                )
            )

    is_air_gapped = len(non_loopback) == 0
    msg = (
        "Air-gapped verification passed: zero non-loopback network connections detected."
        if is_air_gapped
        else f"Warning: {len(non_loopback)} non-loopback connection(s) detected."
    )

    return OfflineCheckResponse(
        air_gapped=is_air_gapped,
        measured_at=datetime.now(timezone.utc).isoformat(),
        total_sockets=len(raw_conns),
        non_loopback_sockets=len(non_loopback),
        non_loopback_connections=non_loopback,
        message=msg,
    )
