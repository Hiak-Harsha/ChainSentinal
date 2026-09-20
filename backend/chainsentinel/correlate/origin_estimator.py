"""First-seen origin IP estimator for Bitcoin transactions."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


@dataclass
class OriginEstimate:
    txid: str
    origin_ip: str
    confidence: float
    delta_t: float
    is_anonymizer: bool
    sensor_count: int
    first_seen_ts: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "txid": self.txid,
            "origin_ip": self.origin_ip,
            "confidence": round(self.confidence, 4),
            "delta_t": round(self.delta_t, 4),
            "is_anonymizer": self.is_anonymizer,
            "sensor_count": self.sensor_count,
            "first_seen_ts": self.first_seen_ts,
        }


class OriginEstimator:
    """Estimates the originating IP address of a transaction from multi-vantage network telemetry."""

    def __init__(self, tau: float = 2.0, anon_penalty: float = 0.35) -> None:
        self.tau = tau  # Diffusion time constant (~2 seconds trickling delay)
        self.anon_penalty = anon_penalty

    def estimate_origin(self, txid: str, observations: list[dict[str, Any]]) -> OriginEstimate | None:
        """Estimate the origin IP for a single transaction.

        Returns OriginEstimate with confidence derived from the gap to the 2nd observation
        and penalized if the earliest observer is an anonymizer/hosting relay.
        """
        if not observations:
            return None

        # Sort observations chronologically
        sorted_obs = sorted(observations, key=lambda x: float(x.get("ts", 0.0)))
        first_obs = sorted_obs[0]
        origin_ip = str(first_obs.get("src_ip", ""))
        first_ts = float(first_obs.get("ts", 0.0))
        is_anon = bool(first_obs.get("is_anonymizer", False))

        # Distinct sensors logging this tx
        sensors = {obs.get("sensor_id") for obs in sorted_obs if obs.get("sensor_id")}
        sensor_count = max(1, len(sensors))

        # Calculate time gap to 2nd observation from a DIFFERENT IP
        delta_t = 0.0
        for next_obs in sorted_obs[1:]:
            next_ip = str(next_obs.get("src_ip", ""))
            if next_ip != origin_ip:
                delta_t = max(0.0, float(next_obs.get("ts", first_ts)) - first_ts)
                break

        if delta_t == 0.0 and len(sorted_obs) > 1:
            delta_t = max(0.0, float(sorted_obs[1].get("ts", first_ts)) - first_ts)

        # Confidence modeling:
        # Gap confidence: grows asymptotically with time gap to 2nd observation
        # gap_score in [0.20, 0.95]
        gap_score = 0.20 + 0.75 * (1.0 - math.exp(-delta_t / self.tau))

        # Penalty for anonymizer / Tor / VPN
        penalty = self.anon_penalty if is_anon else 1.0

        confidence = min(0.99, max(0.05, gap_score * penalty))

        return OriginEstimate(
            txid=txid,
            origin_ip=origin_ip,
            confidence=round(confidence, 4),
            delta_t=round(delta_t, 4),
            is_anonymizer=is_anon,
            sensor_count=sensor_count,
            first_seen_ts=first_ts,
        )

    def estimate_batch(self, obs_by_txid: dict[str, list[dict[str, Any]]]) -> dict[str, OriginEstimate]:
        """Estimate origins for a dictionary of {txid: [observations]}."""
        estimates: dict[str, OriginEstimate] = {}
        for txid, obs_list in obs_by_txid.items():
            est = self.estimate_origin(txid, obs_list)
            if est:
                estimates[txid] = est
        return estimates
