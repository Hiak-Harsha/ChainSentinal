"""
ChainSentinel — Vercel Serverless Function Entry Point.

Unified ASGI handler for deploying both Frontend and Backend on Vercel.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Resolve root and backend directory paths
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

# Ensure backend and root are in sys.path
for p in (BACKEND_DIR, ROOT_DIR):
    str_p = str(p)
    if str_p not in sys.path:
        sys.path.insert(0, str_p)

# Serverless environment overrides (AWS Lambda / Vercel allows writing to /tmp)
os.environ.setdefault("CS_AIR_GAPPED", "false")
os.environ.setdefault("CS_DATA_DIR", "/tmp/chainsentinel/data")
os.environ.setdefault("CS_DB_PATH", "/tmp/chainsentinel/data/chainsentinel.duckdb")
os.environ.setdefault("CS_MODELS_DIR", "/tmp/chainsentinel/data/models")
os.environ.setdefault("CS_EXPORTS_DIR", "/tmp/chainsentinel/data/exports")

# Resolve GeoIP database path
geoip_candidate = ROOT_DIR / "data" / "geoip" / "dbip-country-asn-lite.mmdb"
if geoip_candidate.exists():
    os.environ.setdefault("CS_GEOIP_DB_PATH", str(geoip_candidate))

from app.main import app

# Vercel's Python runtime natively invokes `app`
