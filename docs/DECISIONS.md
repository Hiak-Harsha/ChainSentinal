# ChainSentinel — Decision Log

## D001: Python Version (2024-09-20)
**Decision:** Target Python 3.11+ (spec says 3.11, user has 3.14).
**Rationale:** 3.11 is the minimum for all our deps. Using 3.11 features only for max compatibility.

## D002: GeoIP Database (2024-09-20)
**Decision:** Use a built-in IP→country/ASN lookup table with ~50 real-world ASN/country combos for Phase 1. Stub the maxminddb reader to fall back to this table.
**Rationale:** No .mmdb file available yet. The built-in table produces realistic enrichment for synthetic data. A real GeoLite2/DB-IP file can be dropped in later with zero code changes.

## D003: Development Platform (2024-09-20)
**Decision:** Develop on Windows with cross-platform Python. Linux scripts (install.sh, run.sh, Docker) are stubs until Phase 9.
**Rationale:** User is on Windows. The Python backend and Node.js frontend are fully cross-platform. Linux-specific packaging is Phase 9.

## D004: Frontend Framework (2024-09-20)
**Decision:** Next.js 14 with App Router, `output: 'export'` for static build served by FastAPI.
**Rationale:** Per spec. Single-process deployment (FastAPI serves both API and static UI). No Node.js runtime needed in production.
