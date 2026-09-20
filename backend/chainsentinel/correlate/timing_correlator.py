"""Timing correlation and permutation test for multi-cluster operator detection."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import random
from typing import Any

from chainsentinel.correlate.origin_estimator import OriginEstimate


@dataclass
class SharesOriginLink:
    entity_a: str
    entity_b: str
    shared_ip: str
    co_occurrences: int
    p_value: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_a": self.entity_a,
            "entity_b": self.entity_b,
            "shared_ip": self.shared_ip,
            "co_occurrences": self.co_occurrences,
            "p_value": round(self.p_value, 4),
        }


class TimingCorrelator:
    """Detects co-occurrence of transactions from distinct entities via the same IP within delta_t,
    and runs a Monte Carlo permutation test to compute empirical p-values.
    """

    def __init__(
        self,
        time_window_sec: float = 60.0,
        num_permutations: int = 100,
        p_value_threshold: float = 0.05,
        min_co_occurrences: int = 2,
    ) -> None:
        self.time_window_sec = time_window_sec
        self.num_permutations = num_permutations
        self.p_value_threshold = p_value_threshold
        self.min_co_occurrences = min_co_occurrences

    def find_operator_links(
        self,
        entity_txids: dict[str, list[str]],
        origin_estimates: dict[str, OriginEstimate],
    ) -> list[SharesOriginLink]:
        """Find statistically significant same-operator links between entities."""
        # 1. Map IP -> list of (timestamp, entity_id, txid)
        ip_events: dict[str, list[tuple[float, str, str]]] = defaultdict(list)

        for entity_id, txids in entity_txids.items():
            for txid in txids:
                est = origin_estimates.get(txid)
                if not est or not est.origin_ip:
                    continue
                ip_events[est.origin_ip].append((est.first_seen_ts, entity_id, txid))

        # 2. Count observed co-occurrences per (entity_a, entity_b, ip)
        # Pair key is canonical: (min(ea, eb), max(ea, eb), ip)
        observed_counts: dict[tuple[str, str, str], int] = defaultdict(int)

        for ip, events in ip_events.items():
            if len(events) < 2:
                continue
            # Sort events by timestamp
            sorted_events = sorted(events, key=lambda x: x[0])
            n = len(sorted_events)

            for i in range(n):
                t_i, ent_i, _ = sorted_events[i]
                for j in range(i + 1, n):
                    t_j, ent_j, _ = sorted_events[j]
                    if t_j - t_i > self.time_window_sec:
                        break
                    if ent_i != ent_j:
                        pair_key = (min(ent_i, ent_j), max(ent_i, ent_j), ip)
                        observed_counts[pair_key] += 1

        # Filter candidates meeting minimum co-occurrences
        candidates = {
            pair: count for pair, count in observed_counts.items()
            if count >= self.min_co_occurrences
        }

        if not candidates:
            return []

        # 3. Monte Carlo Permutation Test to calculate empirical p-values
        links: list[SharesOriginLink] = []

        for (ea, eb, ip), k_obs in candidates.items():
            # Get timestamps of transactions for ea and eb at this IP (or overall)
            ts_a = [
                est.first_seen_ts for txid in entity_txids.get(ea, [])
                if (est := origin_estimates.get(txid)) is not None and est.origin_ip == ip
            ]
            ts_b = [
                est.first_seen_ts for txid in entity_txids.get(eb, [])
                if (est := origin_estimates.get(txid)) is not None and est.origin_ip == ip
            ]

            if not ts_a or not ts_b:
                continue

            # Time span
            all_ts = ts_a + ts_b
            t_min, t_max = min(all_ts), max(all_ts)
            span = max(1.0, t_max - t_min)

            count_exceed = 0
            rng = random.Random(42)  # Deterministic seed for reproducible testing

            for _ in range(self.num_permutations):
                # Shuffle timestamps uniformly over the span
                shuffled_a = [t_min + rng.random() * span for _ in ts_a]
                shuffled_b = [t_min + rng.random() * span for _ in ts_b]

                # Count null co-occurrences
                null_k = 0
                for ta in shuffled_a:
                    for tb in shuffled_b:
                        if abs(ta - tb) <= self.time_window_sec:
                            null_k += 1

                if null_k >= k_obs:
                    count_exceed += 1

            p_val = (count_exceed + 1.0) / (self.num_permutations + 1.0)

            if p_val <= self.p_value_threshold:
                links.append(SharesOriginLink(
                    entity_a=ea,
                    entity_b=eb,
                    shared_ip=ip,
                    co_occurrences=k_obs,
                    p_value=p_val,
                ))

        # Sort by p_value ascending, co_occurrences descending
        links.sort(key=lambda x: (x.p_value, -x.co_occurrences))
        return links
