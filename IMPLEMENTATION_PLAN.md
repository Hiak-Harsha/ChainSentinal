# ChainSentinel — Critical Review & Implementation Plan

## Objective

Turn ChainSentinel from a feature-rich prototype into a coherent forensic investigation workspace where every module is a first-class, testable workflow rather than a visual popup. Preserve the existing forensic capabilities while improving correctness, observability, modularity, accessibility, and operator UX.

## Changes implemented in this audit

### 1. Workspace architecture
- Kept the network canvas as the dedicated Network workspace.
- Changed the shared `canvas-overlay` behavior from an absolute translucent overlay to a normal scrollable workspace surface.
- Non-network modules now occupy the primary canvas as full application sections instead of visually sitting on top of the graph.
- The right Inspector remains a persistent contextual rail for selected entities/alerts/traces/cases.

### 2. Ingestion workflow
- Added real file selection and upload controls for CSV/JSON/XML.
- Connected the UI to the existing `/ingest/upload` endpoint.
- Added API methods for individual ingestion jobs and QC reports.
- Removed hard-coded QC claims such as `99.8%` completeness and `0 Violations`.
- QC values now come from the backend report: processed rows, valid rows, quarantine count, duplicates, unique transactions/addresses/IPs, throughput, and quarantine reasons.
- The existing job table remains the source of truth for selecting a run.

### 3. Model Lab correctness
- Removed timer-based fake training progress.
- Model training now starts through the backend asynchronous job runner and polls `/jobs/{job_id}`.
- Progress/stage shown to the analyst now reflects backend job state.
- Fixed the API/UI contract mismatch: the backend now exposes the exact top-level fields consumed by Model Lab.
- Added actual empirical conformal coverage to the training report instead of presenting only the 90% target.
- Exposed supervised feature importances from the persisted classifier.

### 4. Test data
Added small deterministic smoke datasets:
- `backend/data/samples/chainsentinel_smoke_observations.jsonl`
- `backend/data/samples/chainsentinel_smoke_observations.csv`

These are derived from the existing deterministic generated dataset and are intentionally small enough for repeatable manual ingestion tests.

## Remaining implementation work recommended

### A. Complete end-to-end environment setup
1. Install backend dependencies from `backend/pyproject.toml`.
2. Install frontend dependencies with `npm ci`.
3. Confirm Python 3.11+ and a compatible Node version.
4. Start backend and frontend using the documented scripts.
5. Run the full backend and frontend test suites.

### B. Functional acceptance matrix

#### Network
- Load a known entity from the smoke dataset.
- Change hop count 1–4.
- Verify graph redraw and selected-node highlighting.
- Verify empty/unknown entity state.
- Verify clustering job starts, reports progress, completes, and refreshes graph.
- Verify trace/investigation actions pivot to the correct workspace.

#### Alerts
- Load alert list.
- Filter by priority/risk/status.
- Select an alert.
- Verify Inspector loads details and triage actions persist.
- Submit feedback and verify it appears in feedback data.
- Verify no-data and backend-error states are distinguishable.

#### Taint Pathfinder
- Run forward, backward, and both-direction traces.
- Test invalid target.
- Test zero-result trace.
- Test pathfinding with shortest and bottleneck strategies.
- Verify result tables remain usable at narrow viewport widths.

#### Cases
- Generate a case from a known entity.
- Verify case appears in directory.
- Open case and timeline.
- Add a timeline event.
- Export HTML and CSV.
- Verify export errors are surfaced without leaving a dead state.

#### Ingestion
- Upload the smoke CSV.
- Upload the smoke JSONL/JSON-compatible fixture as supported by the parser.
- Test malformed extension.
- Test malformed transaction.
- Test duplicate records.
- Verify quarantine counts and reasons match backend QC.
- Verify selected job changes the QC panel.
- Verify a running job does not display completed metrics.

#### Model Lab
- Start asynchronous training.
- Confirm stage/progress changes are backend-driven.
- Refresh the page during training.
- Verify completed metrics are loaded after refresh.
- Run detection after training.
- Verify new alerts appear in Alert Center.

### C. UI/UX hardening
- Extract repeated inline styles into reusable primitives:
  `PageHeader`, `SectionCard`, `MetricCard`, `DataTable`, `EmptyState`, `ErrorState`, `Toolbar`.
- Add consistent page-level spacing and responsive breakpoints.
- Reduce visual density in large tables.
- Add explicit loading, empty, success, warning, and error states to every data-driven module.
- Replace ambiguous icon-only actions with accessible labels/tooltips.
- Ensure all interactive rows/buttons are keyboard accessible.
- Add focus-visible styles.
- Verify contrast and reduced-motion behavior.
- Add mobile/tablet navigation behavior for the context rail and Inspector.

### D. Reliability
- Add API request cancellation with `AbortController` for rapid navigation.
- Add retry/backoff only where appropriate.
- Avoid duplicate polling loops.
- Clear all intervals/timeouts on unmount.
- Centralize error normalization in `api.js`.
- Add request IDs to backend logs for long-running forensic operations.

### E. Backend/API contract
- Generate or maintain a typed API contract for frontend/backend fields.
- Add response-model validation for high-value endpoints.
- Keep the Model Lab response backward compatible while documenting the stable UI contract.
- Add explicit job states: queued, running, completed, failed, cancelled.

### F. Security
- Confirm API key behavior in production.
- Never expose secrets through Vite build-time variables unless they are intentionally public.
- Keep upload path sanitization and size limits enabled.
- Test malicious filenames and oversized uploads.
- Verify exported case files escape user-controlled HTML correctly.
- Verify WebSocket authentication/authorization if exposed outside localhost.

## Definition of done

The application should satisfy all of the following:
1. Every major module is a first-class workspace, not a popup/overlay.
2. No user-visible metric is hard-coded when a backend value exists.
3. Every long-running operation has real job state and cancellation/cleanup behavior.
4. Every data-driven page has loading, empty, error, and success states.
5. Smoke data can exercise ingestion, graph/entity resolution, alerts, traces, cases, and model workflows.
6. Backend and frontend test suites execute from a clean checkout.
7. Production build completes without warnings that indicate broken imports or missing assets.
8. Keyboard navigation, responsive layouts, and reduced-motion behavior are verified.
9. API contracts used by the frontend are explicitly tested.
10. A clean operator can understand what happened, why it happened, and what action to take without opening modal dialogs just to access basic module content.

## Suggested verification commands

Backend:
```bash
cd backend
python -m pytest -q
```

Frontend:
```bash
cd frontend
npm ci
npm test -- --run
npm run build
```

Manual smoke dataset:
```text
backend/data/samples/chainsentinel_smoke_observations.csv
backend/data/samples/chainsentinel_smoke_observations.jsonl
```
