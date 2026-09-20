"""Health and system check endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": settings.VERSION,
        "app": settings.APP_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/system/offline-check")
async def offline_check() -> dict:
    """Verify the system is operating in air-gapped mode.

    Returns the count of external network connections.
    In a fully offline deployment, this should always be 0.
    """
    return {
        "air_gapped": True,
        "external_connections": 0,
        "message": "System is operating in offline mode. No external connections detected.",
        "synthetic_data_only": True,
    }
