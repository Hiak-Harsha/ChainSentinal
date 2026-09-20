"""Clustering evaluation benchmarks vs ground truth: ARI, NMI, and Pairwise Precision/Recall."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from typing import Any


class ClusterEvaluator:
    """Computes academic-grade clustering benchmarks comparing resolved entities against ground truth."""

    @staticmethod
    def load_ground_truth_map(gt_path: str | Path) -> dict[str, str]:
        """Load address -> true_entity_id mapping from ground_truth.json."""
        with open(gt_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        addr_to_true_ent: dict[str, str] = {}
        for ent in data.get("entities", []):
            ent_id = ent.get("entity_id")
            for addr in ent.get("addresses", []):
                addr_to_true_ent[addr] = ent_id

        return addr_to_true_ent

    @staticmethod
    def evaluate(
        discovered_map: dict[str, str],
        ground_truth_map: dict[str, str],
    ) -> dict[str, Any]:
        """Compute Pairwise Precision, Recall, F1, ARI, and NMI.

        Uses O(N) contingency matrix formulas to ensure instant computation without
        O(N^2) pairwise iteration.
        """
        # Find intersection of evaluated addresses
        common_addrs = [a for a in discovered_map if a in ground_truth_map]
        N = len(common_addrs)
        if N < 2:
            return {
                "evaluated_addresses": N,
                "pairwise_precision": 1.0,
                "pairwise_recall": 1.0,
                "pairwise_f1": 1.0,
                "adjusted_rand_index": 1.0,
                "normalized_mutual_info": 1.0,
            }

        # Build contingency matrix: C[true_k][discovered_c]
        contingency: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        true_counts: dict[str, int] = Counter()
        disc_counts: dict[str, int] = Counter()

        for a in common_addrs:
            t = ground_truth_map[a]
            d = discovered_map[a]
            contingency[t][d] += 1
            true_counts[t] += 1
            disc_counts[d] += 1

        # Calculate TP, TP+FP, TP+FN via binomial combinations: comb(n, 2) = n*(n-1)/2
        tp = 0
        for t, d_map in contingency.items():
            for d, count in d_map.items():
                if count > 1:
                    tp += count * (count - 1) // 2

        sum_comb_disc = sum(c * (c - 1) // 2 for c in disc_counts.values() if c > 1)
        sum_comb_true = sum(c * (c - 1) // 2 for c in true_counts.values() if c > 1)
        total_pairs = N * (N - 1) // 2

        # Pairwise metrics
        pairwise_prec = tp / sum_comb_disc if sum_comb_disc > 0 else 1.0
        pairwise_rec = tp / sum_comb_true if sum_comb_true > 0 else 1.0
        pairwise_f1 = (
            (2 * pairwise_prec * pairwise_rec) / (pairwise_prec + pairwise_rec)
            if (pairwise_prec + pairwise_rec) > 0 else 0.0
        )

        # Adjusted Rand Index (ARI)
        expected_index = (sum_comb_true * sum_comb_disc) / total_pairs if total_pairs > 0 else 0.0
        max_index = 0.5 * (sum_comb_true + sum_comb_disc)
        denom = max_index - expected_index
        ari = (tp - expected_index) / denom if denom > 0 else 1.0

        # Normalized Mutual Information (NMI)
        # H(T), H(D), I(T; D)
        h_true = -sum((c / N) * math.log2(c / N) for c in true_counts.values() if c > 0)
        h_disc = -sum((c / N) * math.log2(c / N) for c in disc_counts.values() if c > 0)

        mi = 0.0
        for t, d_map in contingency.items():
            for d, count in d_map.items():
                if count > 0:
                    p_td = count / N
                    p_t = true_counts[t] / N
                    p_d = disc_counts[d] / N
                    mi += p_td * math.log2(p_td / (p_t * p_d))

        h_mean = 0.5 * (h_true + h_disc)
        nmi = mi / h_mean if h_mean > 0 else 1.0

        return {
            "evaluated_addresses": N,
            "true_entities_count": len(true_counts),
            "discovered_entities_count": len(disc_counts),
            "pairwise_precision": round(pairwise_prec, 4),
            "pairwise_recall": round(pairwise_rec, 4),
            "pairwise_f1": round(pairwise_f1, 4),
            "adjusted_rand_index": round(ari, 4),
            "normalized_mutual_info": round(nmi, 4),
        }
