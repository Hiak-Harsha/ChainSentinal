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


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        app=settings.APP_NAME,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


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
