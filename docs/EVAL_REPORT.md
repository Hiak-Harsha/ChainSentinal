# ChainSentinel — Forensic Pipeline Evaluation Report
### AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic (NTRO SIH26146)

> **Generated:** 2026-09-20 21:12:46 UTC
> **Dataset:** ground_truth.json
> **Target Benchmarks:** `eval/targets.yaml`
> **Deployment Mode:** Strict Offline / Air-Gapped

---

## 1. Executive Summary & Verification Scorecard

| Evaluation Dimension | Metric | Benchmark Result | Target | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Entity Resolution (CIOH)** | Pairwise Precision | **100.0%** | &ge; 95.0% | **PASSED** |
| **Entity Resolution (CIOH)** | Normalized Mutual Info (NMI) | **0.774** | &ge; 0.700 | **PASSED** |
| **Network Attribution** | Overall Top-1 IP Accuracy | **48.1%** | &ge; 45.0% | **PASSED** |
| **Network Attribution** | Overall Top-3 IP Accuracy | **54.1%** | &ge; 50.0% | **PASSED** |
| **Typology Classification** | Multi-Class Accuracy | **88.9%** | &ge; 85.0% | **PASSED** |
| **Typology Classification** | Macro F1-Score | **67.8%** | &ge; 70.0% | **FAILED** |
| **Unseen Hold-out Anomaly** | Anomaly Separation (&Delta;) | **+0.362** | &ge; +0.300 | **PASSED** |
| **Unseen Hold-out Anomaly** | Hold-out Anomaly Catch Rate | **43.3%** | &ge; 40.0% | **PASSED** |

---

## 2. Entity Clustering & Resolution (CIOH + CoinJoin Protection)

Common-Input-Ownership Heuristic (CIOH) clustering implemented via Disjoint-Set / Union-Find with path compression, strictly guarded by multi-party CoinJoin transaction isolation.

- **Evaluated Addresses:** `936`
- **Pairwise Precision:** `1.0000`
- **Pairwise Recall:** `0.0151`
- **Pairwise F1-Score:** `0.0298`
- **Adjusted Rand Index (ARI):** `0.0286`
- **Normalized Mutual Information (NMI):** `0.7738`

---

## 3. Network⇄Blockchain Attribution Across Obfuscation Levels

First-seen origin estimation with TF-IDF hub relay de-biasing and Monte Carlo permutation null hypothesis testing ($p \le 0.05$).

| Obfuscation Level | Description | Top-1 Accuracy | Top-3 Accuracy | Evaluated Entities |
| :---: | :--- | :---: | :---: | :---: |
| **Level 0** | None (Direct broadcast) | 47.4% | 52.6% | 116 |
| **Level 1** | Low (Random trickling delay) | 41.1% | 49.3% | 73 |
| **Level 2** | Medium (Multi-hop proxy relay) | 56.2% | 58.3% | 48 |
| **Level 3** | High (Tor / VPN / Anonymizer pool) | 54.5% | 63.6% | 33 |

---

## 4. Unseen Hold-Out Typology Experiment (Proof of Real AI/ML)

To prove inductive generalization beyond hardcoded rules, an unsupervised Isolation Forest anomaly detector was evaluated on unseen hold-out typologies `T8 (Dusting)` and `T9 (Multi-Cluster Operator)`.

- **Legitimate Baseline Anomaly Mean:** `0.104`
- **Unseen Hold-out Typology Anomaly Mean:** `0.466`
- **Empirical Separation Delta (&Delta;):** `+0.362`
- **Unseen Hold-out Flagging Rate:** `43.3%`

---

## 5. System Throughput & Processing Benchmarks

- **Database Backend:** DuckDB (In-Process Columnar OLAP)
- **Monitored Transactions:** `1,248`
- **Monitored Observations:** `6,239`
- **Resolved Entities:** `2,515`
- **Active Risk Alerts:** `0`
- **Evaluation Run Latency:** `6.396s`


---
*ChainSentinel Forensic Intelligence Engine — Confidential / Law Enforcement & Defense Use Only*