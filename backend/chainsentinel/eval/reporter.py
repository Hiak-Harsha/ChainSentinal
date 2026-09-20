"""Comprehensive forensic evaluation and benchmark reporter against ground truth."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any
import yaml

from chainsentinel.eval.cluster_eval import ClusterEvaluator
from chainsentinel.eval.correlate_eval import CorrelateEvaluator
from chainsentinel.models.pipeline import ModelPipeline
from chainsentinel.storage.db import DatabaseManager
from chainsentinel.trace.agent import AutonomousInvestigator


def load_eval_targets(custom_path: str | Path | None = None) -> dict[str, Any]:
    """Load evaluation target thresholds from the single source of truth (targets.yaml)."""
    candidates = [
        Path(custom_path) if custom_path else None,
        Path(__file__).resolve().parent / "targets.yaml",
        Path(__file__).resolve().parents[3] / "eval" / "targets.yaml",
        Path("eval/targets.yaml"),
    ]
    for c in candidates:
        if c and c.exists():
            with open(c, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def _evaluate_metric(
    actual: float | None, target: float, comparator: str = ">="
) -> tuple[str, str]:
    """Compare actual metric with target and return (formatted_target, verdict)."""
    sym = "&ge;" if comparator == ">=" else ("&le;" if comparator == "<=" else comparator)
    target_fmt = f"{sym} {target * 100:.1f}%" if target <= 1.0 else f"{sym} {target:.3f}"

    if actual is None:
        return target_fmt, "**NOT RUN**"

    passed = False
    if comparator == ">=":
        passed = actual >= target
    elif comparator == "<=":
        passed = actual <= target
    elif comparator == ">":
        passed = actual > target
    elif comparator == "<":
        passed = actual < target

    verdict = "**PASSED**" if passed else "**FAILED**"
    return target_fmt, verdict


class ForensicReporter:
    """Computes academic-grade forensic benchmarks and generates evaluation reports."""

    def __init__(self, db: DatabaseManager, ground_truth_path: str | Path):
        self.db = db
        self.gt_path = Path(ground_truth_path)

    def run_full_evaluation(self) -> dict[str, Any]:
        """Execute end-to-end quantitative evaluation across clustering, attribution, and ML."""
        conn = self.db.conn
        t0 = time.time()

        # 1. Clustering Evaluation
        addr_entity_rows = conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall()
        discovered_map = {r[0]: str(r[1]) for r in addr_entity_rows}

        if self.gt_path.exists():
            true_map = ClusterEvaluator.load_ground_truth_map(self.gt_path)
            cluster_metrics = ClusterEvaluator.evaluate(discovered_map, true_map)
        else:
            cluster_metrics = {
                "evaluated_addresses": len(discovered_map),
                "status": "ground_truth_unavailable",
            }

        # 2. IP Attribution Evaluation
        attr_rows = conn.execute("SELECT entity_id, ip, score, posterior_prob FROM ip_entity_links").fetchall()
        attributions: dict[str, list[dict[str, Any]]] = {}
        for eid, ip, score, post in attr_rows:
            if eid not in attributions:
                attributions[eid] = []
            attributions[eid].append({
                "ip": str(ip),
                "score": float(score) if score is not None else 0.0,
                "posterior": float(post) if post is not None else 0.0,
            })

        if self.gt_path.exists():
            attr_metrics = CorrelateEvaluator.evaluate_attribution(
                attributions=attributions,
                ground_truth_path=self.gt_path,
                address_entity_map=discovered_map,
            )
        else:
            attr_metrics = {
                "overall": {"total_evaluated": len(attributions)},
                "status": "ground_truth_unavailable",
            }

        # 3. Supervised & Unsupervised Model Evaluation
        pipeline = ModelPipeline(db=self.db)
        if self.gt_path.exists():
            train_res = pipeline.train(ground_truth_path=self.gt_path)
            supervised_metrics = train_res.get("metrics", {})
            holdout_res = pipeline.evaluate_holdout(ground_truth_path=self.gt_path)
        else:
            supervised_metrics = {"status": "ground_truth_unavailable"}
            holdout_res = {"status": "ground_truth_unavailable"}

        # 4. Database & Throughput Telemetry
        tx_count_row = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
        entity_count_row = conn.execute("SELECT COUNT(*) FROM entities").fetchone()
        obs_count_row = conn.execute("SELECT COUNT(*) FROM observations").fetchone()
        alerts_count_row = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()

        elapsed_sec = max(0.01, time.time() - t0)

        results = {
            "evaluation_timestamp": time.time(),
            "telemetry": {
                "total_observations": int(obs_count_row[0]) if obs_count_row else 0,
                "total_transactions": int(tx_count_row[0]) if tx_count_row else 0,
                "total_entities": int(entity_count_row[0]) if entity_count_row else 0,
                "total_alerts": int(alerts_count_row[0]) if alerts_count_row else 0,
                "evaluation_runtime_sec": round(elapsed_sec, 3),
            },
            "clustering": cluster_metrics,
            "attribution": attr_metrics,
            "supervised_classification": supervised_metrics,
            "unsupervised_holdout_experiment": holdout_res,
        }
        return results

    def generate_markdown_report(
        self,
        eval_results: dict[str, Any],
        output_path: str | Path | None = None,
        targets_path: str | Path | None = None,
    ) -> str:
        """Render evaluation report as GitHub-flavored Markdown comparing against targets.yaml."""
        targets = load_eval_targets(targets_path)
        t = eval_results.get("telemetry", {})
        c = eval_results.get("clustering", {})
        a = eval_results.get("attribution", {})
        s = eval_results.get("supervised_classification", {})
        h = eval_results.get("unsupervised_holdout_experiment", {})

        top1_acc = a.get("overall_top1_accuracy")
        if top1_acc is None:
            top1_acc = a.get("overall", {}).get("top1_accuracy")
        top3_acc = a.get("overall_top3_accuracy")
        if top3_acc is None:
            top3_acc = a.get("overall", {}).get("top3_accuracy")

        # Scorecard item evaluations against targets.yaml
        t_clust = targets.get("clustering", {})
        t_attr = targets.get("attribution", {})
        t_sup = targets.get("supervised_classification", {})
        t_unsup = targets.get("unsupervised_holdout_experiment", {})

        # Precision
        pw_prec = c.get("pairwise_precision")
        tgt_prec = t_clust.get("pairwise_precision", {}).get("target", 0.95)
        cmp_prec = t_clust.get("pairwise_precision", {}).get("comparator", ">=")
        tgt_prec_fmt, v_prec = _evaluate_metric(pw_prec, tgt_prec, cmp_prec)
        val_prec_fmt = f"**{pw_prec * 100:.1f}%**" if pw_prec is not None else "N/A"

        # NMI
        nmi = c.get("normalized_mutual_info")
        tgt_nmi = t_clust.get("normalized_mutual_info", {}).get("target", 0.70)
        cmp_nmi = t_clust.get("normalized_mutual_info", {}).get("comparator", ">=")
        tgt_nmi_fmt, v_nmi = _evaluate_metric(nmi, tgt_nmi, cmp_nmi)
        val_nmi_fmt = f"**{nmi:.3f}**" if nmi is not None else "N/A"

        # Top 1 IP
        tgt_top1 = t_attr.get("overall_top1_accuracy", {}).get("target", 0.80)
        cmp_top1 = t_attr.get("overall_top1_accuracy", {}).get("comparator", ">=")
        tgt_top1_fmt, v_top1 = _evaluate_metric(top1_acc, tgt_top1, cmp_top1)
        val_top1_fmt = f"**{top1_acc * 100:.1f}%**" if top1_acc is not None else "N/A"

        # Top 3 IP
        tgt_top3 = t_attr.get("overall_top3_accuracy", {}).get("target", 0.90)
        cmp_top3 = t_attr.get("overall_top3_accuracy", {}).get("comparator", ">=")
        tgt_top3_fmt, v_top3 = _evaluate_metric(top3_acc, tgt_top3, cmp_top3)
        val_top3_fmt = f"**{top3_acc * 100:.1f}%**" if top3_acc is not None else "N/A"

        # Accuracy
        acc = s.get("accuracy")
        tgt_acc = t_sup.get("accuracy", {}).get("target", 0.90)
        cmp_acc = t_sup.get("accuracy", {}).get("comparator", ">=")
        tgt_acc_fmt, v_acc = _evaluate_metric(acc, tgt_acc, cmp_acc)
        val_acc_fmt = f"**{acc * 100:.1f}%**" if acc is not None else "N/A"

        # F1 Macro
        f1 = s.get("f1_macro")
        tgt_f1 = t_sup.get("f1_macro", {}).get("target", 0.85)
        cmp_f1 = t_sup.get("f1_macro", {}).get("comparator", ">=")
        tgt_f1_fmt, v_f1 = _evaluate_metric(f1, tgt_f1, cmp_f1)
        val_f1_fmt = f"**{f1 * 100:.1f}%**" if f1 is not None else "N/A"

        # Separation Delta
        sep = h.get("anomaly_separation_delta")
        tgt_sep = t_unsup.get("anomaly_separation_delta", {}).get("target", 0.30)
        cmp_sep = t_unsup.get("anomaly_separation_delta", {}).get("comparator", ">=")
        tgt_sep_fmt, v_sep = _evaluate_metric(sep, tgt_sep, cmp_sep)
        val_sep_fmt = f"**+{sep:.3f}**" if sep is not None else "N/A"

        # Anomaly Flagged Ratio
        flag_ratio = h.get("flagged_as_anomalous_ratio")
        tgt_flag = t_unsup.get("flagged_as_anomalous_ratio", {}).get("target", 0.80)
        cmp_flag = t_unsup.get("flagged_as_anomalous_ratio", {}).get("comparator", ">=")
        tgt_flag_fmt, v_flag = _evaluate_metric(flag_ratio, tgt_flag, cmp_flag)
        val_flag_fmt = f"**{flag_ratio * 100:.1f}%**" if flag_ratio is not None else "N/A"

        fmt_prec = f"{c['pairwise_precision']:.4f}" if c.get("pairwise_precision") is not None else "N/A"
        fmt_rec = f"{c['pairwise_recall']:.4f}" if c.get("pairwise_recall") is not None else "N/A"
        fmt_f1 = f"{c['pairwise_f1']:.4f}" if c.get("pairwise_f1") is not None else "N/A"
        fmt_ari = f"{c['adjusted_rand_index']:.4f}" if c.get("adjusted_rand_index") is not None else "N/A"
        fmt_nmi_score = f"{c['normalized_mutual_info']:.4f}" if c.get("normalized_mutual_info") is not None else "N/A"

        fmt_legit_m = f"{h['legitimate_anomaly_mean']:.3f}" if h.get("legitimate_anomaly_mean") is not None else "N/A"
        fmt_holdout_m = f"{h['holdout_anomaly_mean']:.3f}" if h.get("holdout_anomaly_mean") is not None else "N/A"
        fmt_sep_d = f"+{h['anomaly_separation_delta']:.3f}" if h.get("anomaly_separation_delta") is not None else "N/A"
        fmt_flag_r = f"{h['flagged_as_anomalous_ratio'] * 100:.1f}%" if h.get("flagged_as_anomalous_ratio") is not None else "N/A"

        report_lines = [
            "# ChainSentinel — Forensic Pipeline Evaluation Report",
            "### AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic (NTRO SIH26146)",
            "",
            "> **Generated:** " + time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(eval_results.get("evaluation_timestamp", time.time()))),
            "> **Dataset:** " + str(self.gt_path.name),
            "> **Target Benchmarks:** `eval/targets.yaml`",
            "> **Deployment Mode:** Strict Offline / Air-Gapped",
            "",
            "---",
            "",
            "## 1. Executive Summary & Verification Scorecard",
            "",
            "| Evaluation Dimension | Metric | Benchmark Result | Target | Verdict |",
            "| :--- | :--- | :--- | :--- | :--- |",
            f"| **Entity Resolution (CIOH)** | Pairwise Precision | {val_prec_fmt} | {tgt_prec_fmt} | {v_prec} |",
            f"| **Entity Resolution (CIOH)** | Normalized Mutual Info (NMI) | {val_nmi_fmt} | {tgt_nmi_fmt} | {v_nmi} |",
            f"| **Network Attribution** | Overall Top-1 IP Accuracy | {val_top1_fmt} | {tgt_top1_fmt} | {v_top1} |",
            f"| **Network Attribution** | Overall Top-3 IP Accuracy | {val_top3_fmt} | {tgt_top3_fmt} | {v_top3} |",
            f"| **Typology Classification** | Multi-Class Accuracy | {val_acc_fmt} | {tgt_acc_fmt} | {v_acc} |",
            f"| **Typology Classification** | Macro F1-Score | {val_f1_fmt} | {tgt_f1_fmt} | {v_f1} |",
            f"| **Unseen Hold-out Anomaly** | Anomaly Separation (&Delta;) | {val_sep_fmt} | {tgt_sep_fmt} | {v_sep} |",
            f"| **Unseen Hold-out Anomaly** | Hold-out Anomaly Catch Rate | {val_flag_fmt} | {tgt_flag_fmt} | {v_flag} |",
            "",
            "---",
            "",
            "## 2. Entity Clustering & Resolution (CIOH + CoinJoin Protection)",
            "",
            "Common-Input-Ownership Heuristic (CIOH) clustering implemented via Disjoint-Set / Union-Find with path compression, strictly guarded by multi-party CoinJoin transaction isolation.",
            "",
            f"- **Evaluated Addresses:** `{c.get('evaluated_addresses', 'N/A')}`",
            f"- **Pairwise Precision:** `{fmt_prec}`",
            f"- **Pairwise Recall:** `{fmt_rec}`",
            f"- **Pairwise F1-Score:** `{fmt_f1}`",
            f"- **Adjusted Rand Index (ARI):** `{fmt_ari}`",
            f"- **Normalized Mutual Information (NMI):** `{fmt_nmi_score}`",
            "",
            "---",
            "",
            "## 3. Network⇄Blockchain Attribution Across Obfuscation Levels",
            "",
            "First-seen origin estimation with TF-IDF hub relay de-biasing and Monte Carlo permutation null hypothesis testing ($p \\le 0.05$).",
            "",
            "| Obfuscation Level | Description | Top-1 Accuracy | Top-3 Accuracy | Evaluated Entities |",
            "| :---: | :--- | :---: | :---: | :---: |",
        ]

        by_lvl = a.get("by_obfuscation_level", {})
        lvl_names = {
            "0": "None (Direct broadcast)",
            "1": "Low (Random trickling delay)",
            "2": "Medium (Multi-hop proxy relay)",
            "3": "High (Tor / VPN / Anonymizer pool)",
        }
        for lvl in ["0", "1", "2", "3"]:
            stats = by_lvl.get(lvl) or by_lvl.get(f"level_{lvl}")
            if stats:
                t_count = stats.get("total_entities", stats.get("total", 0))
                top1 = f"{stats.get('top1_accuracy', 0.0) * 100:.1f}%"
                top3 = f"{stats.get('top3_accuracy', 0.0) * 100:.1f}%"
            else:
                t_count = 0
                top1 = "N/A"
                top3 = "N/A"
            report_lines.append(
                f"| **Level {lvl}** | {lvl_names.get(lvl, 'Obfuscated')} | {top1} | {top3} | {t_count} |"
            )

        report_lines.extend([
            "",
            "---",
            "",
            "## 4. Unseen Hold-Out Typology Experiment (Proof of Real AI/ML)",
            "",
            "To prove inductive generalization beyond hardcoded rules, an unsupervised Isolation Forest anomaly detector was evaluated on unseen hold-out typologies `T8 (Dusting)` and `T9 (Multi-Cluster Operator)`.",
            "",
            f"- **Legitimate Baseline Anomaly Mean:** `{fmt_legit_m}`",
            f"- **Unseen Hold-out Typology Anomaly Mean:** `{fmt_holdout_m}`",
            f"- **Empirical Separation Delta (&Delta;):** `{fmt_sep_d}`",
            f"- **Unseen Hold-out Flagging Rate:** `{fmt_flag_r}`",
            "",
            "---",
            "",
            "## 5. System Throughput & Processing Benchmarks",
            "",
            f"- **Database Backend:** DuckDB (In-Process Columnar OLAP)",
            f"- **Monitored Transactions:** `{t.get('total_transactions', 0):,}`",
            f"- **Monitored Observations:** `{t.get('total_observations', 0):,}`",
            f"- **Resolved Entities:** `{t.get('total_entities', 0):,}`",
            f"- **Active Risk Alerts:** `{t.get('total_alerts', 0):,}`",
            f"- **Evaluation Run Latency:** `{t.get('evaluation_runtime_sec', 0.0):.3f}s`",
            "",
            "",
            "---",
            "*ChainSentinel Forensic Intelligence Engine — Confidential / Law Enforcement & Defense Use Only*",
        ])

        report_content = "\n".join(report_lines)

        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(report_content, encoding="utf-8")
            # Also emit metrics.json
            metrics_json_path = out_p.parent / "metrics.json"
            metrics_json_path.write_text(json.dumps(eval_results, indent=2), encoding="utf-8")

        return report_content

    def export_sample_dossier(self, output_path: str | Path | None = None) -> str:
        """Generate and export a court-admissible sample case file."""
        conn = self.db.conn
        row = conn.execute("SELECT entity_id FROM alerts ORDER BY risk_score DESC LIMIT 1").fetchone()
        if not row:
            row = conn.execute("SELECT entity_id FROM entities LIMIT 1").fetchone()

        if not row:
            return ""

        target_entity = row[0]
        agent = AutonomousInvestigator(self.db)
        case = agent.investigate(target=target_entity, max_hops=3, decay_model="proportional")

        dossier_lines = [
            "# Forensic Investigative Case Dossier",
            f"**Case ID:** `{case['case_id']}`",
            f"**Target Entity:** `{case['target_id']}`",
            f"**Triage Status:** `{case['status']}`",
            f"**Tamper-Evident SHA-256 Digest:** `{case['bundle_hash']}`",
            f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(case['created_at']))}",
            "",
            "---",
            "",
            case.get("narrative_report", ""),
            "",
            "---",
            "## Evidentiary Integrity Seal",
            f"This dossier and its attached Cytoscape graph bundle ({len(case.get('cytoscape_subgraph', {}).get('elements', {}).get('nodes', []))} nodes, {len(case.get('cytoscape_subgraph', {}).get('elements', {}).get('edges', []))} edges) are sealed with canonical SHA-256 digest:",
            f"```\n{case['bundle_hash']}\n```",
            "Any modification to timestamps, addresses, or satoshi amounts invalidates this signature.",
        ]

        content = "\n".join(dossier_lines)
        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(content, encoding="utf-8")

        return content
