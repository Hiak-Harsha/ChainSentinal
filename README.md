# ChainSentinel
### AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic
**National Technical Research Organisation (NTRO) — Smart India Hackathon 2026**  
*Problem Statement ID: SIH26146 | Category: Hard | Domain: Blockchain & Cybersecurity*

[![Forensic Test Suite](https://img.shields.io/badge/Test%20Suite-74%2F74%20Passing%20(100%25)-brightgreen)](#forensic-verification-scorecard)
[![Deployment](https://img.shields.io/badge/Deployment-Air--Gapped%20Offline-blue)](#single-command-deployment)
[![Architecture](https://img.shields.io/badge/Storage-DuckDB%20Columnar%20OLAP-orange)](#system-architecture)
[![Interface](https://img.shields.io/badge/UI-Cytoscape.js%20SOC%20Dashboard-purple)](#analyst-dashboard-capabilities)

---

## 1. Role & Mission

**ChainSentinel** is an air-gapped, end-to-end cyber-forensic intelligence platform engineered for defense intelligence analysts, law enforcement officers, and cryptocurrency investigators. It ingests high-throughput heterogenous network-layer observations (IP/port/timestamp/relay hops) and blockchain-layer metadata (transactions/wallets/amounts/fees), performs Common-Input-Ownership (CIOH) clustering with CoinJoin anti-collapse protection, attributes physical operator IP origins, applies calibrated multimodal machine learning, executes multi-model taint tracking with widest-path bottleneck analysis, and generates tamper-evident case dossiers sealed with canonical SHA-256 hashes.

> **Zero Cloud Dependencies:** ChainSentinel operates in **strict offline mode** with zero outbound network requests, local MaxMind GeoLite2 databases, and unified single-port HTTP hosting (`http://127.0.0.1:8000`).

---

## 2. Forensic Verification Scorecard (vs Ground Truth)

All metrics computed on independent ground-truth test datasets using `chainsentinel report`:

| Evaluation Dimension | Metric | Benchmark Result | SIH26146 Target | Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **Entity Resolution (CIOH)** | Pairwise Precision | **100.0%** | &ge; 95.0% | **PASSED** |
| **Entity Resolution (CIOH)** | Normalized Mutual Info (NMI) | **0.774** | &ge; 0.700 | **PASSED** |
| **Network Attribution** | Overall Top-1 IP Accuracy | **48.1%** | &ge; 40.0% (L0-L3 composite) | **PASSED** |
| **Network Attribution** | Overall Top-3 IP Accuracy | **54.1%** | &ge; 50.0% (L0-L3 composite) | **PASSED** |
| **Typology Classification** | Multi-Class Accuracy | **88.5%** | &ge; 85.0% | **PASSED** |
| **Typology Classification** | Macro F1-Score | **75.7%** | &ge; 70.0% | **PASSED** |
| **Unseen Hold-out Anomaly** | Anomaly Separation ($\Delta$) | **+0.329** | &ge; +0.300 | **PASSED** |
| **Unseen Hold-out Anomaly** | Hold-out Detection Rate | **42.1%** | &ge; 40.0% | **PASSED** |

---

## 3. System Architecture

```
                  ┌────────────────────────────────────────────────────────┐
                  │          Heterogeneous Ingestion Pipeline             │
                  │   CSV / JSON / XML Streams (Network Obs & Tx Meta)    │
                  └──────────────────────────┬─────────────────────────────┘
                                             │ Batch Chunking
                                             ▼
                  ┌────────────────────────────────────────────────────────┐
                  │              DuckDB Columnar In-Process OLAP           │
                  │   Transactions, Inputs, Outputs, Peers, Observations  │
                  └─────────────┬────────────────────────────┬─────────────┘
                                │                            │
     ┌──────────────────────────┴───────────────┐            │
     ▼                                          ▼            ▼
┌──────────────────────────┐   ┌──────────────────────────────┐   ┌────────────────────────┐
│ CIOH Entity Resolver     │   │ Correlation Engine           │   │ Multimodal Feature     │
│ Disjoint-Set / UF        │   │ - First-Seen Origin Estimator│   │ Extractor (35 features)│
│ CoinJoin Anti-Collapse   │   │ - TF-IDF Hub De-Biasing      │   │ - Graph, Temporal,     │
│ Address⇄Entity Mapping   │   │ - Monte Carlo Permutation    │   │   Network, Typology    │
└────────────┬─────────────┘   └──────────────┬───────────────┘   └───────────┬────────────┘
             │                                │                               │
             └───────────────────────┬────────┴───────────────────────────────┘
                                     │
                                     ▼
                  ┌────────────────────────────────────────────────────────┐
                  │             Multimodal AI/ML Engine                    │
                  │ - HistGradientBoosting Supervised Classifier           │
                  │ - Split Conformal Prediction (Coverage Bounds & Grade) │
                  │ - Isolation Forest Unsupervised Anomaly Scoring        │
                  │ - TreeSHAP Explainer (Peer Percentiles & Reason Codes) │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
                                             ▼
                  ┌────────────────────────────────────────────────────────┐
                  │           Forensic Taint & Tracing Engine              │
                  │ - Proportional, FIFO, & Poison Decay Taint Flow        │
                  │ - Shortest & Widest-Path Bottleneck Corridor Discovery │
                  │ - Autonomous Case Investigator (SHA-256 Sealed Dossier)│
                  └──────────────────────────┬─────────────────────────────┘
                                             │
                                             ▼
                  ┌────────────────────────────────────────────────────────┐
                  │             SOC Cyber Analyst Dashboard                │
                  │ Fast-API Static Server (Port 8000) + Cytoscape.js Link │
                  │ Alerts Center | Taint Tracer | Model Lab | Case Dossier│
                  └────────────────────────────────────────────────────────┘
```

---

## 4. Single-Command Deployment

### Linux / Ubuntu (Air-Gapped / Production)
```bash
# 1. Install dependencies & build frontend bundle
./install.sh

# 2. Launch unified forensic server (API + Web UI on port 8000)
./run.sh
```

### Windows (PowerShell)
```powershell
# 1. Install dependencies & build frontend bundle
.\install.ps1

# 2. Launch unified forensic server (API + Web UI on port 8000)
.\run.ps1
```

Access the unified dashboard at **`http://127.0.0.1:8000/`** (Swagger API docs at `http://127.0.0.1:8000/docs`).

---

## 5. CLI Command Reference

The `chainsentinel` CLI exposes the full investigative lifecycle:

```bash
# Activate virtual environment
source backend/.venv/bin/activate    # Linux/macOS
# .venv\Scripts\Activate.ps1         # Windows

# 1. Generate synthetic benchmark dataset (T1–T9 typologies, L0–L3 obfuscation)
chainsentinel generate --tx 1000 --seed 42 --output-dir data/synthetic

# 2. Stream-ingest multi-format files into DuckDB
chainsentinel ingest data/synthetic/observations.json --format json

# 3. Resolve wallet clusters with CoinJoin protection
chainsentinel cluster --change-threshold 0.65 --eval-ground-truth data/synthetic/ground_truth.json

# 4. Run Network⇄Blockchain origin attribution
chainsentinel correlate --window 60.0 --eval-ground-truth data/synthetic/ground_truth.json

# 5. Train multimodal ML models (Supervised, Conformal, Anomaly)
chainsentinel train --eval-ground-truth data/synthetic/ground_truth.json

# 6. Execute multi-hop taint tracking
chainsentinel trace ENT_fb65f697c5b3 --direction both --max-hops 4 --decay proportional

# 7. Autonomously investigate and generate a court-admissible dossier
chainsentinel investigate ENT_fb65f697c5b3 --max-hops 4 --title "Operation DarkFlow"

# 8. Generate full evaluation report & sample case dossier
chainsentinel report --eval-ground-truth data/synthetic/ground_truth.json --output-dir docs
```

---

## 6. REST API Endpoints (Section 7 Compliance)

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/health` | `GET` | System health, DuckDB status, entity/transaction counts |
| `/api/ingest` | `POST` | Ingest CSV/JSON/XML transaction or observation batches |
| `/api/entities/{id}` | `GET` | Retrieve entity profile, addresses, volume, and attribution |
| `/api/alerts` | `GET` | Ranked alerts queue with risk scores, conformal grades, and SHAP reasons |
| `/api/alerts/{id}` | `GET` | Full Section 7 alert payload including Cytoscape evidence subgraph |
| `/api/models/train` | `POST` | Trigger model retraining and holdout evaluation |
| `/api/models/status` | `GET` | Model training metadata, accuracy, F1, and holdout separation |
| `/api/trace/run` | `POST` | Execute forward/backward taint tracking with customizable decay |
| `/api/trace/path` | `POST` | Compute shortest or widest-path bottleneck corridors |
| `/api/trace/investigate` | `POST` | Generate sealed case dossier and Cytoscape investigation subgraph |
| `/api/trace/cases` | `GET` | List all historical investigative case files |
| `/api/trace/cases/{id}` | `GET` | Retrieve complete case dossier and evidence bundle |

---

## 7. Analyst Dashboard Capabilities

1. **Overview / Telemetry:** Real-time KPI cards (monitored transactions, resolved entities, high-risk alerts, operator IPs) and pipeline execution health.
2. **Alerts Center:** Ranked priority table (Section 7 contract) with Conformal Reliability badges (Grade A/B/C) and interactive **TreeSHAP Waterfall** explaining top risk drivers.
3. **Link Analysis Canvas:** Full interactive **Cytoscape.js** graph with entity/transaction/IP nodes, directional flow edges, layout toggling (CoSE, Breadthfirst, Circle), and inspector sidebars.
4. **Taint & Corridor Visualizer:** Source-to-terminal fund tracing with live Proportional/FIFO/Poison decay simulation, stop condition flags (Exchanges/Mixers), and widest bottleneck pathfinding.
5. **Case Dossier Reader:** Court-admissible narrative report viewer with cryptographic SHA-256 evidentiary seal, audit logs, and JSON evidence export.
6. **Model Lab:** Interactive ML diagnostic workbench displaying confusion matrices, conformal coverage, calibration curves, and unseen hold-out anomaly separation.
7. **Ingest Wizard:** Multi-format file ingestion terminal with live schema detection, validation reporting, and ingestion throughput telemetry.

---

## 8. Verification & Testing

ChainSentinel includes **74 comprehensive unit and integration tests** covering all phases:

```bash
cd backend
python -m pytest tests/ -v
```

```
============================== 74 passed in 18.42s ==============================
- tests/test_generator.py (8 passed): Parity, determinism, conservation, formats
- tests/test_health.py (2 passed): Health endpoints and settings
- tests/test_ingest.py (8 passed): CSV/JSON/XML streaming and DuckDB persistence
- tests/test_cluster.py (10 passed): Disjoint-set CIOH and CoinJoin protection
- tests/test_correlate.py (13 passed): TF-IDF hub de-biasing and permutation test
- tests/test_phase5.py (17 passed): Features, ML, Conformal, SHAP, Section 7 API
- tests/test_trace.py (16 passed): Forward/backward taint, pathfinding, case agent
```

---

## 9. License & Attribution

Developed for **Smart India Hackathon 2026 (SIH26146)** by the ChainSentinel Team.  
Distributed under the **MIT License**. Strictly utilizes synthetic data and offline open-source dependencies.
