"""Risk-prioritized investigative alert generation conforming to the Section 7 NTRO API contract."""

from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Any

from chainsentinel.storage.db import DatabaseManager


class AlertGenerator:
    """Computes composite risk priority scores and generates forensic alert bundles."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def compute_risk_score(
        self,
        p_supervised: float,
        anomaly_score: float,
        volume_sat: float,
        is_legitimate: bool = False,
    ) -> tuple[float, float]:
        """Compute composite risk score and operational priority.
        
        Formula:
          risk_score = 0.50 * P(illicit) + 0.30 * anomaly_score + 0.20 * volume_factor
        """
        # If predicted class is legitimate, illicit probability is 1.0 - P(legitimate)
        p_illicit = (1.0 - p_supervised) if is_legitimate else p_supervised
        p_illicit = max(0.0, min(1.0, float(p_illicit)))

        anom = max(0.0, min(1.0, float(anomaly_score)))

        # Volume factor logarithmically scales up to 10 BTC (1,000,000,000 satoshis)
        vol = max(0.0, float(volume_sat))
        if vol > 0:
            vol_factor = min(1.0, math.log10(vol + 1.0) / 9.0)
        else:
            vol_factor = 0.0

        risk_score = (0.50 * p_illicit) + (0.30 * anom) + (0.20 * vol_factor)
        risk_score = round(float(np_clip(risk_score, 0.0, 1.0)), 4)

        # Priority is risk score weighted by volume and anomaly severity
        priority = round(min(1.0, risk_score * 1.05), 4)
        return risk_score, priority

    def generate_evidence_bundle(self, entity_id: str) -> dict[str, Any]:
        """Fetch associated transactions, IPs, and compute tamper-evident SHA-256 bundle hash."""
        conn = self.db.conn

        # Fetch member addresses
        addrs = [
            r[0]
            for r in conn.execute(
                "SELECT address FROM address_entity_map WHERE entity_id = ?", [entity_id]
            ).fetchall()
        ]

        # Fetch transaction IDs
        tx_rows = conn.execute(
            """
            WITH ent_addrs AS (
                SELECT address FROM address_entity_map WHERE entity_id = ?
            )
            SELECT DISTINCT txid FROM (
                SELECT i.txid FROM tx_inputs i JOIN ent_addrs a ON i.address = a.address
                UNION ALL
                SELECT o.txid FROM tx_outputs o JOIN ent_addrs a ON o.address = a.address
            )
            LIMIT 100
            """,
            [entity_id],
        ).fetchall()
        txids = sorted([r[0] for r in tx_rows])

        # Fetch associated IPs
        ip_rows = conn.execute(
            "SELECT ip FROM ip_entity_links WHERE entity_id = ? ORDER BY posterior_prob DESC LIMIT 20",
            [entity_id],
        ).fetchall()
        ips = [r[0] for r in ip_rows]

        subgraph_ref = f"/api/graph/subgraph?entity_id={entity_id}"

        # Canonical evidence structure for deterministic hashing
        canonical_evidence = {
            "entity_id": entity_id,
            "addresses": sorted(addrs[:50]),
            "txids": txids[:50],
            "ips": ips[:20],
            "subgraph_ref": subgraph_ref,
        }
        evidence_bytes = json.dumps(canonical_evidence, sort_keys=True).encode("utf-8")
        bundle_hash = hashlib.sha256(evidence_bytes).hexdigest()

        return {
            "txids": txids,
            "ips": ips,
            "subgraph_ref": subgraph_ref,
            "bundle_hash": bundle_hash,
        }

    def fetch_attribution_summary(self, entity_id: str) -> dict[str, Any]:
        """Retrieve the primary origin IP attribution and network basis."""
        conn = self.db.conn
        row = conn.execute(
            """
            SELECT ip, score, posterior_prob, n_tx, first_seen_ratio
            FROM ip_entity_links
            WHERE entity_id = ?
            ORDER BY posterior_prob DESC, score DESC
            LIMIT 1
            """,
            [entity_id],
        ).fetchone()

        if row:
            ip, score, post_prob, n_tx, fs_ratio = row
            obs_row = conn.execute(
                "SELECT src_country, src_asn, sensor_id FROM observations WHERE src_ip = ? LIMIT 1",
                [ip],
            ).fetchone()
            country = obs_row[0] if obs_row and obs_row[0] else "UNKNOWN"
            asn = obs_row[1] if obs_row and obs_row[1] else "UNKNOWN"

            basis = (
                f"Attributed via TF-IDF posterior P={post_prob:.2f} across {n_tx} txs "
                f"({fs_ratio*100:.1f}% first-seen by sensors)"
            )
            return {
                "ip": str(ip),
                "asn": str(asn),
                "country": str(country),
                "confidence": round(float(post_prob), 4),
                "basis": basis,
            }
        else:
            return {
                "ip": "UNKNOWN",
                "asn": "UNKNOWN",
                "country": "UNKNOWN",
                "confidence": 0.0,
                "basis": "No definitive network origin IP established.",
            }

    def build_alert(
        self,
        entity_id: str,
        predicted_class: str,
        calibrated_p: float,
        anomaly_score: float,
        volume_sat: float,
        conformal_set: list[str],
        grade: str,
        reasons: list[dict[str, Any]],
        top_k_typologies: list[tuple[str, float]] | None = None,
    ) -> dict[str, Any]:
        """Build and return an alert dictionary complying with Section 7 API contract."""
        is_legit = predicted_class.upper() == "LEGITIMATE"
        risk_score, priority = self.compute_risk_score(
            p_supervised=calibrated_p,
            anomaly_score=anomaly_score,
            volume_sat=volume_sat,
            is_legitimate=is_legit,
        )

        alert_id = f"ALT-{entity_id.replace('ENT-', '')}-{int(time.time())}"
        now = time.time()

        # Evidence and Attribution
        evidence = self.generate_evidence_bundle(entity_id)
        attribution = self.fetch_attribution_summary(entity_id)

        # Typologies list
        if top_k_typologies:
            typologies = [
                {
                    "name": name,
                    "strength": round(float(strength), 4),
                    "txids": evidence["txids"][:10],
                }
                for name, strength in top_k_typologies
                if name.upper() != "LEGITIMATE"
            ]
        else:
            typologies = [
                {
                    "name": predicted_class,
                    "strength": round(float(calibrated_p), 4),
                    "txids": evidence["txids"][:10],
                }
            ]

        alert_payload = {
            "alert_id": alert_id,
            "entity_id": entity_id,
            "priority": priority,
            "risk_score": risk_score,
            "status": "NEW",
            "created_at": now,
            "confidence": {
                "calibrated_p": round(float(calibrated_p), 4),
                "conformal_set": conformal_set,
                "grade": grade,
            },
            "typologies": typologies,
            "reasons": reasons,
            "attribution": attribution,
            "evidence": evidence,
        }

        return alert_payload


def np_clip(val: float, low: float, high: float) -> float:
    return max(low, min(high, val))
