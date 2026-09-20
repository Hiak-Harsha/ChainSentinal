# Forensic Investigative Case Dossier
**Case ID:** `CASE-441EEE2F-1789923431`
**Target Entity:** `ENT_441eee2fc1c0`
**Triage Status:** `OPEN`
**Tamper-Evident SHA-256 Digest:** `123359bdcacb43e925ec41247ed6c6b61e30d5a13bbfdeebde5ecde56a06bfdb`
**Generated:** 2026-09-20 16:57:11 UTC

---

# Forensic Investigation Case File: ENT_441eee2fc1c0
**Classification:** `MIXER` | **Risk Score:** `0.68` | **Monitored Addresses:** `1`

## 1. Executive Summary
Subject entity `ENT_441eee2fc1c0` was subjected to multi-hop autonomous taint tracking and network attribution.
Total cumulative historical inflow is **0 satoshis** across monitored transactions, with historical outflow of **5,017,080 satoshis**.

## 2. Liquidation & Cash-out Analysis (Forward Taint)
- Forward hops analyzed: `0`
- Cash-out exchange destinations identified: None detected within hop horizon.

## 3. Funding Origin Analysis (Backward Taint)
- Backward hops analyzed: `41`
- Upstream funding sources identified: `ENT_0c5c92c426a6`, `ENT_0d042dd709e4`, `ENT_0e82b2891421`, `ENT_107a997517f3`, `ENT_113aa9d8f669`, `ENT_2636c7b0a149`, `ENT_2eb7205254e8`, `ENT_3082b88c2e7c`, `ENT_3575110927f2`, `ENT_37e1fd1f59ae`, `ENT_3c4bf95c83ca`, `ENT_3e09c6ac6ab8`, `ENT_428225688dd1`, `ENT_42dd9345183c`, `ENT_441eee2fc1c0`, `ENT_4c0febb1285b`, `ENT_5a0be9792f96`, `ENT_6077579c14ff`, `ENT_6cb9b0b00c33`, `ENT_7182f49698d9`, `ENT_7ac690d1a044`, `ENT_88a0a23a3362`, `ENT_8bba64c76920`, `ENT_8c6e9ac8392b`, `ENT_986bc546138e`, `ENT_99e204e57b63`, `ENT_a768500b9bb1`, `ENT_ac80fb55b466`, `ENT_c08d5d2a1cba`, `ENT_c196aeb1e30f`, `ENT_c481a4625b9a`, `ENT_c8500627cfd3`, `ENT_ce6181b6c894`, `ENT_ced7758f4b4c`, `ENT_d2c650e90b9c`, `ENT_de05cd42a9b6`, `ENT_df8e20129d78`, `ENT_e17c74e1f940`, `ENT_e87ea19acb23`, `ENT_f2d74a4f76c5`, `ENT_fc9f2bee7749`

## 4. Network Infrastructure & Operator Attribution
- Attributed Broadcast IPs: `49.32.20.74`
- Co-Origin / Shared Infrastructure Entities: `ENT_ced7758f4b4c`, `ENT_3575110927f2`, `ENT_f2d74a4f76c5`, `ENT_c481a4625b9a`, `ENT_7ac690d1a044`

## 5. Recommendation
Target entity exhibits suspicious topological features consistent with layered fund dispersion.

---
## Evidentiary Integrity Seal
This dossier and its attached Cytoscape graph bundle (42 nodes, 62 edges) are sealed with canonical SHA-256 digest:
```
123359bdcacb43e925ec41247ed6c6b61e30d5a13bbfdeebde5ecde56a06bfdb
```
Any modification to timestamps, addresses, or satoshi amounts invalidates this signature.