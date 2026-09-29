# ChainSentinel Critical Audit

## Executive summary

The project has a broad forensic feature set and a meaningful automated-test foundation, but several integration and UX issues prevented it from being considered production-ready from the supplied checkout.

### Critical findings

| Severity | Finding | Status |
|---|---|---|
| High | Backend test collection fails because required runtime dependencies are not installed in the supplied environment (`slowapi`, `duckdb`, `maxminddb`) | Environment issue; documented |
| High | Frontend test command cannot execute from the supplied checkout because `node_modules` is absent/incomplete | Environment issue; documented |
| High | Model Lab frontend expected fields that the backend `/models/lab` endpoint did not return at the top level | Fixed |
| High | Model Lab training progress was simulated with timers rather than tied to the backend job lifecycle | Fixed |
| High | Ingestion UI showed hard-coded quality claims instead of the selected job's QC report | Fixed |
| Medium | Ingestion screen was called a wizard but had no file-upload action | Fixed |
| Medium | Non-network modules were rendered as translucent absolute overlays on top of the Network Canvas | Fixed |
| Medium | Conformal UI displayed a 90% target even when empirical coverage was not returned by the backend | Fixed; empirical coverage now calculated |
| Medium | Large feature components contain substantial inline styling and duplicated page scaffolding | Partially addressed; modular component extraction remains recommended |

## Verification performed

### Backend

The test suite was invoked with:

```bash
cd backend
python -m pytest -q
```

Collection stopped before test execution because the environment was missing:

- `slowapi`
- `maxminddb`
- `duckdb`

Therefore the original checkout could not provide a valid pass/fail test result for the backend.

The modified Python files were syntax-checked successfully with `py_compile`.

### Frontend

The test suite was invoked with:

```bash
cd frontend
npm test -- --run
```

The original checkout reported `vitest: Permission denied`. An attempted dependency installation could not complete because external package registry access was unavailable in the audit environment. Consequently, the frontend suite could not be executed to completion here.

## UI findings

### Workspace architecture

The application used a three-column shell with:

- Context rail
- Primary canvas
- Persistent Inspector

That is a good foundation. The problem was that the Network Canvas remained in the primary canvas while other views were inserted as absolute `.canvas-overlay` layers. This created a visual hierarchy in which Alerts, Cases, Model Lab, Ingestion, and Taint Pathfinder looked like modal overlays instead of application destinations.

The fix changes the overlay surface into a normal document-flow workspace. The network canvas can remain mounted for state preservation, but it is visually hidden when another workspace is active.

### Ingestion

The previous UI displayed:

- `99.8%` completeness
- `0 Violations` for multiple checks

without deriving those values from the selected job. That is unsafe for a forensic application because an analyst can interpret those values as evidence.

The revised UI reads the actual QC report and shows:

- rows processed
- valid rows
- quarantined rows
- duplicate rows
- unique transactions
- unique addresses
- unique IPs
- throughput
- quarantine reasons

It also provides a real file-upload control.

### Model Lab

The frontend and backend had a contract mismatch. The backend returned metrics under `models`, while the frontend expected:

- `supervised_metrics`
- `conformal`
- `holdout_experiment`
- `feature_importances`

The API now provides those stable top-level fields while retaining the existing `models` map.

Training progress previously advanced through client-side `setTimeout` calls. It now starts an actual backend asynchronous job and polls its status.

## Test data added

Small deterministic fixtures were added under:

```text
backend/data/samples/chainsentinel_smoke_observations.jsonl
backend/data/samples/chainsentinel_smoke_observations.csv
```

They are derived from the existing deterministic generated dataset so they are suitable for repeatable ingestion smoke tests without requiring a large multi-megabyte fixture.

## Recommended next acceptance gate

Before calling the application production-ready:

1. Install all backend dependencies.
2. Install frontend dependencies from the lockfile.
3. Run all backend tests.
4. Run all frontend tests.
5. Build the frontend.
6. Start backend + frontend together.
7. Execute the smoke dataset through ingestion.
8. Verify graph/entity resolution.
9. Verify model training and detection.
10. Verify alert triage.
11. Verify trace and pathfinder.
12. Generate and export a case dossier.
13. Repeat the workflow at desktop, tablet, and narrow viewport sizes.
