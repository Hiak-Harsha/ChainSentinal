"""Hub-relay de-biasing and TF-IDF entity-to-IP association matrix."""

from __future__ import annotations

from collections import Counter, defaultdict
import math
from typing import Any

from chainsentinel.correlate.origin_estimator import OriginEstimate


class AssociationMatrix:
    """Computes TF-IDF hub-debiased entity-to-IP associations and posterior probabilities."""

    def __init__(self) -> None:
        pass

    def compute_associations(
        self,
        entity_txids: dict[str, list[str]],
        origin_estimates: dict[str, OriginEstimate],
    ) -> dict[str, list[dict[str, Any]]]:
        """Compute top candidate IPs for each entity.

        Args:
            entity_txids: Mapping of entity_id -> list of txids broadcast by that entity
            origin_estimates: Mapping of txid -> OriginEstimate

        Returns:
            Mapping of entity_id -> list of ranked IP attributions:
            [{
                "ip": "...",
                "score": 4.12,
                "posterior_prob": 0.88,
                "n_tx": 14,
                "first_seen_ratio": 0.875,
                "basis": "14/16 txs (87.5%) first-seen at IP"
            }, ...]
        """
        # 1. Calculate TF per (entity, ip) and count unique entities per IP
        # tf[entity_id][ip] = sum of origin confidence
        # tx_counts[entity_id][ip] = count of txs first-seen from ip
        tf: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        tx_counts: dict[str, Counter[str]] = defaultdict(Counter)
        ip_entity_presence: dict[str, set[str]] = defaultdict(set)

        for entity_id, txids in entity_txids.items():
            for txid in txids:
                est = origin_estimates.get(txid)
                if not est or not est.origin_ip:
                    continue
                ip = est.origin_ip
                tf[entity_id][ip] += est.confidence
                tx_counts[entity_id][ip] += 1
                ip_entity_presence[ip].add(entity_id)

        total_entities = max(1, len(entity_txids))

        # 2. Calculate IDF per IP (Hub-Relay De-biasing)
        # Omnipresent peer relays seen across many entities receive near-zero IDF
        idf: dict[str, float] = {}
        for ip, entities_seen in ip_entity_presence.items():
            n_seen = len(entities_seen)
            # Standard smooth IDF formula
            idf[ip] = math.log(1.0 + (total_entities / (1.0 + n_seen)))

        # 3. Derive TF-IDF scores and posterior probabilities per entity
        attributions: dict[str, list[dict[str, Any]]] = {}

        for entity_id, txids in entity_txids.items():
            ip_tf = tf.get(entity_id, {})
            if not ip_tf:
                attributions[entity_id] = []
                continue

            total_tx = len(txids)
            scores: dict[str, float] = {}
            for ip, term_freq in ip_tf.items():
                scores[ip] = term_freq * idf.get(ip, 1.0)

            total_score = sum(scores.values())

            # Sort IPs by score descending
            ranked_ips: list[dict[str, Any]] = []
            for ip, raw_score in sorted(scores.items(), key=lambda x: -x[1]):
                n_first = tx_counts[entity_id][ip]
                ratio = n_first / max(1, total_tx)
                post_prob = (raw_score / total_score) if total_score > 0 else 0.0

                basis_text = (
                    f"{n_first}/{total_tx} txs ({ratio * 100:.1f}%) first-seen at IP"
                )

                ranked_ips.append({
                    "ip": ip,
                    "entity_id": entity_id,
                    "score": round(raw_score, 4),
                    "posterior_prob": round(post_prob, 4),
                    "n_tx": n_first,
                    "first_seen_ratio": round(ratio, 4),
                    "basis": basis_text,
                })

            attributions[entity_id] = ranked_ips

        return attributions
