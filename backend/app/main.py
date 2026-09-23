"""
ChainSentinel — AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic.

FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.graph import router as graph_router
from app.api.correlate import router as correlate_router
from app.api.alerts import router as alerts_router
from app.api.models import router as models_router
from app.api.trace import router as trace_router
from app.api.ws import router as ws_router
from app.api.jobs import router as jobs_router
from app.core.audit import AuditLogMiddleware
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.security import verify_api_key, _ensure_api_key

# Rate limiter — shared across all routers
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    # Initialize structured logging
    setup_logging()
    # Ensure data directories exist
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    (settings.DATA_DIR / "audit").mkdir(parents=True, exist_ok=True)
    (settings.DATA_DIR / "uploads").mkdir(parents=True, exist_ok=True)
    (settings.DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
    # Ensure API key is generated on first run
    _ensure_api_key()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic (NTRO)",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Ensure structured logging is initialized immediately
setup_logging()

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Audit logging middleware (forensic chain-of-custody)
app.add_middleware(AuditLogMiddleware)

# CORS — localhost only, tightened methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)

# API routes — health is public, all others require API key auth
app.include_router(health_router, prefix="/api")
app.include_router(ingest_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(graph_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(correlate_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(alerts_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(models_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(trace_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(jobs_router, prefix="/api", dependencies=[Depends(verify_api_key)])
app.include_router(ws_router, prefix="/api")
app.include_router(ws_router)

# Serve static frontend if the build exists
frontend_path = Path(settings.FRONTEND_DIR)
if not frontend_path.exists():
    for candidate in [
        Path("frontend/out"),
        Path("../frontend/out"),
        Path(__file__).resolve().parents[2] / "frontend" / "out",
    ]:
        if candidate.exists():
            frontend_path = candidate
            break

if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
