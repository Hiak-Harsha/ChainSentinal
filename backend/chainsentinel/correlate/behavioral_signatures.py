"""Behavioral network signatures: ports, IP churn, ASN diversity, and circadian entropy."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import datetime
import math
from typing import Any


@dataclass
class NetworkSignature:
    entity_id: str
    non_standard_port_ratio: float
    ip_churn_rate: float
    asn_count: int
    anonymizer_ratio: float
    circadian_entropy: float
    geo_hop_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "non_standard_port_ratio": round(self.non_standard_port_ratio, 4),
            "ip_churn_rate": round(self.ip_churn_rate, 4),
            "asn_count": self.asn_count,
            "anonymizer_ratio": round(self.anonymizer_ratio, 4),
            "circadian_entropy": round(self.circadian_entropy, 4),
            "geo_hop_count": self.geo_hop_count,
        }


class BehavioralSignatureExtractor:
    """Extracts port distributions, churn rates, ASN diversity, and circadian entropy for an entity."""

    @staticmethod
    def extract(
        entity_id: str,
        observations: list[dict[str, Any]],
        tx_count: int,
    ) -> NetworkSignature:
        """Extract behavioral network signature from observations of an entity's transactions."""
        if not observations:
            return NetworkSignature(
                entity_id=entity_id,
                non_standard_port_ratio=0.0,
                ip_churn_rate=0.0,
                asn_count=0,
                anonymizer_ratio=0.0,
                circadian_entropy=0.0,
                geo_hop_count=0,
            )

        total_obs = len(observations)

        # 1. Non-standard ports (standard Bitcoin mainnet P2P port is 8333)
        non_standard_count = sum(
            1 for o in observations
            if o.get("src_port") not in (8333, None) and o.get("dst_port") not in (8333, None)
        )
        non_standard_ratio = non_standard_count / max(1, total_obs)

        # 2. IP churn rate: unique IPs / tx_count
        unique_ips = {o.get("src_ip") for o in observations if o.get("src_ip")}
        ip_churn = len(unique_ips) / max(1, tx_count)

        # 3. ASN diversity
        asns = {o.get("src_asn") for o in observations if o.get("src_asn")}
        asn_count = len(asns)

        # 4. Anonymizer ratio
        anon_count = sum(1 for o in observations if o.get("is_anonymizer"))
        anonymizer_ratio = anon_count / max(1, total_obs)

        # 5. Circadian hour-of-day Shannon entropy
        # 24 bins for hours 0..23 in UTC
        hour_counts = Counter()
        for o in observations:
            ts = float(o.get("ts", 0.0))
            if ts > 0:
                dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                hour_counts[dt.hour] += 1

        entropy = 0.0
        if hour_counts:
            max_entropy = math.log2(24.0)
            for count in hour_counts.values():
                p = count / total_obs
                if p > 0:
                    entropy -= p * math.log2(p)
            circadian_entropy = entropy / max_entropy  # normalized in [0, 1]
        else:
            circadian_entropy = 0.0

        # 6. Geo hops: consecutive observations within 1 hour switching countries
        # Sort chronologically
        sorted_obs = sorted(observations, key=lambda x: float(x.get("ts", 0.0)))
        geo_hops = 0
        prev_country = None
        prev_ts = None

        for o in sorted_obs:
            country = o.get("src_country")
            ts = float(o.get("ts", 0.0))
            if prev_country and country and country != prev_country:
                if prev_ts and (ts - prev_ts) <= 3600.0:
                    geo_hops += 1
            prev_country = country
            prev_ts = ts

        return NetworkSignature(
            entity_id=entity_id,
            non_standard_port_ratio=round(non_standard_ratio, 4),
            ip_churn_rate=round(ip_churn, 4),
            asn_count=asn_count,
            anonymizer_ratio=round(anonymizer_ratio, 4),
            circadian_entropy=round(circadian_entropy, 4),
            geo_hop_count=geo_hops,
        )
