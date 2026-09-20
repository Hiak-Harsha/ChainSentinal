"""Evaluation benchmarks for IP attribution vs ground truth across obfuscation levels."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any


class CorrelateEvaluator:
    """Evaluates Top-1 and Top-3 IP attribution accuracy against ground truth."""

    @staticmethod
    def evaluate_attribution(
        attributions: dict[str, list[dict[str, Any]]],
        ground_truth_path: str | Path,
        address_entity_map: dict[str, str],
    ) -> dict[str, Any]:
        """Evaluate IP attribution accuracy against ground_truth.json.

        Returns overall Top-1/Top-3 accuracy and breakdown by obfuscation level.
        """
        with open(ground_truth_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

        # 1. Map true addresses to true entity details
        addr_to_gt_ent: dict[str, dict[str, Any]] = {}
        for ent in gt_data.get("entities", []):
            op_ips = ent.get("operator_ips", [])
            if ent.get("operator_ip") and ent["operator_ip"] not in op_ips:
                op_ips.append(ent["operator_ip"])

            obf_level = ent.get("obfuscation_level", 0)

            ent_info = {
                "entity_id": ent.get("entity_id"),
                "operator_ips": set(op_ips),
                "obfuscation_level": obf_level,
                "typology": ent.get("typology", "UNKNOWN"),
            }
            for addr in ent.get("addresses", []):
                addr_to_gt_ent[addr] = ent_info

        # 2. Map discovered entities to true entities by majority address vote
        disc_ent_addrs: dict[str, list[str]] = defaultdict(list)
        for addr, disc_ent_id in address_entity_map.items():
            disc_ent_addrs[disc_ent_id].append(addr)

        total_evaluated = 0
        top1_correct = 0
        top3_correct = 0

        # Per-level counters: {level: [correct_top1, correct_top3, total]}
        level_stats: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0])

        for disc_ent_id, addrs in disc_ent_addrs.items():
            # Find true entity by majority vote
            gt_votes: Counter[str] = Counter()
            for a in addrs:
                gt_ent = addr_to_gt_ent.get(a)
                if gt_ent and gt_ent.get("entity_id"):
                    gt_votes[gt_ent["entity_id"]] += 1

            if not gt_votes:
                continue

            majority_gt_id = gt_votes.most_common(1)[0][0]
            # Find representative gt_ent
            rep_gt = next(
                (addr_to_gt_ent[a] for a in addrs if addr_to_gt_ent.get(a, {}).get("entity_id") == majority_gt_id),
                None,
            )
            if not rep_gt or not rep_gt["operator_ips"]:
                continue

            true_ips = rep_gt["operator_ips"]
            obf = rep_gt["obfuscation_level"]

            # Check discovered top candidate IPs
            candidates = attributions.get(disc_ent_id, [])
            if not candidates:
                continue

            total_evaluated += 1
            level_stats[obf][2] += 1

            # Top 1 check
            top1_ip = candidates[0]["ip"]
            if top1_ip in true_ips:
                top1_correct += 1
                level_stats[obf][0] += 1

            # Top 3 check
            top3_ips = {c["ip"] for c in candidates[:3]}
            if any(tip in true_ips for tip in top3_ips):
                top3_correct += 1
                level_stats[obf][1] += 1

        overall_top1 = (top1_correct / total_evaluated) if total_evaluated > 0 else 0.0
        overall_top3 = (top3_correct / total_evaluated) if total_evaluated > 0 else 0.0

        by_obfuscation: dict[str, dict[str, float]] = {}
        for lvl in sorted(level_stats.keys()):
            c1, c3, tot = level_stats[lvl]
            by_obfuscation[f"level_{lvl}"] = {
                "total_entities": tot,
                "top1_accuracy": round(c1 / tot, 4) if tot > 0 else 0.0,
                "top3_accuracy": round(c3 / tot, 4) if tot > 0 else 0.0,
            }

        return {
            "total_entities_evaluated": total_evaluated,
            "overall_top1_accuracy": round(overall_top1, 4),
            "overall_top3_accuracy": round(overall_top3, 4),
            "by_obfuscation_level": by_obfuscation,
        }
