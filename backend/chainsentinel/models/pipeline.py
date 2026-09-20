"""End-to-end ML pipeline coordinating feature extraction, training, conformal calibration, and alert generation."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any
import numpy as np

from chainsentinel.alerts.alert_generator import AlertGenerator
from chainsentinel.explain.explainer import ForensicExplainer
from chainsentinel.features.extractor import MultimodalFeatureExtractor
from chainsentinel.models.conformal import ConformalPredictor
from chainsentinel.models.supervised import SupervisedTypologyClassifier
from chainsentinel.models.unsupervised import IsolationForestAnomalyDetector
from chainsentinel.storage.db import DatabaseManager


class ModelPipeline:
    """Orchestrates model lifecycle: feature engineering, training, conformal calibration, and detection."""

    def __init__(self, db: DatabaseManager, model_dir: str | Path = "data/models"):
        self.db = db
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.extractor = MultimodalFeatureExtractor(db)
        self.alert_gen = AlertGenerator(db)

    def _resolve_labels_from_ground_truth(
        self, entity_features: list[dict[str, Any]], gt_path: Path | str | None
    ) -> list[str]:
        """Map entity IDs to ground truth typology names, or infer from entity metadata."""
        gt_map: dict[str, str] = {}
        if gt_path and Path(gt_path).exists():
            with open(gt_path, "r", encoding="utf-8") as f:
                gt_data = json.load(f)
            
            # Map by wallet/address to entity mapping
            conn = self.db.conn
            addr_ent = dict(conn.execute("SELECT address, entity_id FROM address_entity_map").fetchall())

            typ_norm = {
                "peel_chain": "T1_PEEL_CHAIN",
                "coinjoin": "T2_COINJOIN",
                "ransomware": "T3_RANSOMWARE",
                "darknet": "T4_DARKNET",
                "extortion": "T5_EXTORTION",
                "layering": "T6_LAYERING",
                "structuring": "T7_STRUCTURING",
                "dusting": "T8_DUSTING",
                "multi_cluster": "T9_MULTI_CLUSTER_OPERATOR",
                "multi_cluster_operator": "T9_MULTI_CLUSTER_OPERATOR",
            }

            clusters = gt_data.get("entities") or gt_data.get("entity_clusters") or []
            for cluster in clusters:
                raw_typ = cluster.get("typology") or (
                    "LEGITIMATE" if cluster.get("type") == "legit" else cluster.get("archetype")
                )
                if not raw_typ or str(raw_typ).lower() in ("legit", "none", "null"):
                    typ = "LEGITIMATE"
                else:
                    norm_k = str(raw_typ).lower()
                    typ = typ_norm.get(norm_k, str(raw_typ).upper())

                c_id = cluster.get("entity_id") or cluster.get("cluster_id")
                if c_id:
                    gt_map[str(c_id)] = typ
                w_list = cluster.get("addresses") or cluster.get("wallets") or []
                for w in w_list:
                    if w in addr_ent:
                        gt_map[addr_ent[w]] = typ

            # Also check illicit campaigns
            camp_tx_map = {}
            for camp in gt_data.get("campaigns", []):
                typ = camp.get("typology") or "ILLICIT"
                for txid in camp.get("txids", []):
                    camp_tx_map[txid] = typ

            if camp_tx_map:
                all_txids = list(camp_tx_map.keys())
                tx_to_ents = conn.execute(
                    """
                    WITH target_txs AS (SELECT unnest(?) as txid),
                    tx_addrs AS (
                        SELECT i.txid, i.address FROM tx_inputs i JOIN target_txs t ON i.txid = t.txid
                        UNION ALL
                        SELECT o.txid, o.address FROM tx_outputs o JOIN target_txs t ON o.txid = t.txid
                    )
                    SELECT DISTINCT a.entity_id, t.txid
                    FROM tx_addrs t
                    JOIN address_entity_map a ON t.address = a.address
                    """,
                    [all_txids],
                ).fetchall()
                for ent_id, txid in tx_to_ents:
                    if txid in camp_tx_map:
                        gt_map[ent_id] = camp_tx_map[txid]

        labels = []
        conn = self.db.conn
        for ef in entity_features:
            eid = ef["entity_id"]
            if eid in gt_map:
                labels.append(gt_map[eid])
            else:
                # Check entity_type from DB
                row = conn.execute("SELECT entity_type FROM entities WHERE entity_id = ?", [eid]).fetchone()
                etype = row[0] if row else "INDIVIDUAL"
                if etype in ("EXCHANGE", "SERVICE", "INDIVIDUAL"):
                    labels.append("LEGITIMATE")
                elif etype == "MIXER":
                    labels.append("T2_COINJOIN")
                else:
                    labels.append("LEGITIMATE")

        return labels

    def train(
        self,
        ground_truth_path: str | Path | None = "data/cli_test/ground_truth.json",
        random_state: int = 42,
    ) -> dict[str, Any]:
        """Train supervised multi-class model, conformal predictor, and unsupervised anomaly detector."""
        # 1. Extract and save all entity features
        features_data = self.extractor.extract_all_and_save()
        if not features_data:
            return {"status": "error", "message": "No entities found to train on."}

        # 2. Extract labels
        labels = self._resolve_labels_from_ground_truth(features_data, ground_truth_path)

        # 3. Train/Cal/Test Split (60% train, 20% cal, 20% test)
        n = len(features_data)
        indices = np.arange(n)
        rng = np.random.default_rng(random_state)
        rng.shuffle(indices)

        n_train = max(1, int(n * 0.60))
        n_cal = max(1, int(n * 0.20))

        idx_train = indices[:n_train]
        idx_cal = indices[n_train : n_train + n_cal]
        idx_test = indices[n_train + n_cal :]
        if len(idx_test) == 0:
            idx_test = idx_cal

        X_train = [features_data[i]["features"] for i in idx_train]
        y_train = [labels[i] for i in idx_train]

        X_cal = [features_data[i]["features"] for i in idx_cal]
        y_cal = [labels[i] for i in idx_cal]

        X_test = [features_data[i]["features"] for i in idx_test]
        y_test = [labels[i] for i in idx_test]

        # 4. Supervised Model
        clf = SupervisedTypologyClassifier(random_state=random_state)
        clf.fit(X_train, y_train)

        # 5. Conformal Predictor Calibration
        probs_cal = clf.predict_proba(X_cal)
        conformal = ConformalPredictor(default_alpha=0.10)
        conformal.calibrate(probs_cal, y_cal, clf.classes_)

        # 6. Unsupervised Anomaly Detector
        all_X = [ef["features"] for ef in features_data]
        anomaly_model = IsolationForestAnomalyDetector(contamination=0.15, random_state=random_state)
        anomaly_model.fit(all_X)

        # 7. Evaluate
        eval_metrics = clf.evaluate(X_test, y_test)
        test_probs = clf.predict_proba(X_test)
        conf_sets = conformal.predict_sets(test_probs, alpha=0.10)
        avg_set_size = float(np.mean([s["set_size"] for s in conf_sets]))
        grade_dist = {
            "A": sum(1 for s in conf_sets if s["grade"] == "A"),
            "B": sum(1 for s in conf_sets if s["grade"] == "B"),
            "C": sum(1 for s in conf_sets if s["grade"] == "C"),
        }

        # 8. Save models
        clf.save(self.model_dir / "supervised_model.pkl")
        conformal.save(self.model_dir / "conformal_model.pkl")
        anomaly_model.save(self.model_dir / "anomaly_model.pkl")

        report = {
            "status": "success",
            "entities_trained": n,
            "classes": clf.classes_,
            "metrics": {
                "accuracy": eval_metrics["accuracy"],
                "precision_macro": eval_metrics["precision_macro"],
                "recall_macro": eval_metrics["recall_macro"],
                "f1_macro": eval_metrics["f1_macro"],
                "f1_weighted": eval_metrics["f1_weighted"],
            },
            "conformal": {
                "avg_set_size": avg_set_size,
                "grade_distribution": grade_dist,
            },
            "top_features": sorted(
                clf.feature_importances_.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "trained_at": time.time(),
        }

        # Persist metrics to DB
        self.db.save_model_metrics("supervised_typology", report["metrics"])
        self.db.save_model_metrics("conformal_predictor", report["conformal"])
        return report

    def detect(
        self,
        min_risk_score: float = 0.35,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Run full detection pipeline on all entities and generate prioritized alerts."""
        # 1. Load models
        clf_path = self.model_dir / "supervised_model.pkl"
        conf_path = self.model_dir / "conformal_model.pkl"
        anom_path = self.model_dir / "anomaly_model.pkl"

        if not clf_path.exists() or not conf_path.exists() or not anom_path.exists():
            # Automatically train if models not yet saved
            self.train()

        clf = SupervisedTypologyClassifier.load(clf_path)
        conformal = ConformalPredictor.load(conf_path)
        anomaly_model = IsolationForestAnomalyDetector.load(anom_path)

        # 2. Extract / load all features
        features_data = self.extractor.extract_all_and_save()
        if not features_data:
            return []

        all_feats = [fd["features"] for fd in features_data]
        all_eids = [fd["entity_id"] for fd in features_data]

        # 3. Model predictions
        probs = clf.predict_proba(all_feats)
        conformal_res = conformal.predict_sets(probs, alpha=0.10)
        anomaly_scores = anomaly_model.score_samples(all_feats)

        # 4. Explainer
        explainer = ForensicExplainer(clf, all_feats)

        # 5. Generate alerts
        alerts_to_save = []
        for i, eid in enumerate(all_eids):
            feat_dict = all_feats[i]
            top_class = conformal_res[i]["top_class"]
            calibrated_p = conformal_res[i]["calibrated_p"]
            anom_s = float(anomaly_scores[i])
            vol = feat_dict.get("total_volume_sat", 0.0)

            # Quick risk check before building evidence bundle
            is_legit = top_class.upper() == "LEGITIMATE"
            pre_risk, _ = self.alert_gen.compute_risk_score(
                p_supervised=calibrated_p,
                anomaly_score=anom_s,
                volume_sat=vol,
                is_legitimate=is_legit,
            )
            if pre_risk < min_risk_score:
                continue

            # Compute top-k typologies
            top_k = []
            for c_idx in np.argsort(probs[i])[::-1][:3]:
                top_k.append((clf.classes_[c_idx], float(probs[i, c_idx])))

            # Generate natural language reasons
            reasons = explainer.explain_entity(
                entity_id=eid,
                feature_dict=feat_dict,
                predicted_class=top_class,
                class_prob=calibrated_p,
                top_n=4,
            )

            alert = self.alert_gen.build_alert(
                entity_id=eid,
                predicted_class=top_class,
                calibrated_p=calibrated_p,
                anomaly_score=anom_s,
                volume_sat=vol,
                conformal_set=conformal_res[i]["conformal_set"],
                grade=conformal_res[i]["grade"],
                reasons=reasons,
                top_k_typologies=top_k,
            )

            alerts_to_save.append(alert)

        # Sort by priority descending
        alerts_to_save.sort(key=lambda a: (a["priority"], a["risk_score"]), reverse=True)
        selected_alerts = alerts_to_save[:limit]

        # Save to DB
        if selected_alerts:
            self.db.insert_alerts_batch(selected_alerts)

        return selected_alerts

    def evaluate_holdout(
        self,
        ground_truth_path: str | Path = "data/cli_test/ground_truth.json",
        holdout_labels: set[str] | None = None,
    ) -> dict[str, Any]:
        """Hold-Out Typology Experiment: verify unsupervised anomaly detection on unseen typologies."""
        if holdout_labels is None:
            holdout_labels = {"T8_DUSTING", "T9_MULTI_CLUSTER_OPERATOR", "dusting", "multi_cluster"}

        features_data = self.extractor.extract_all_and_save()
        labels = self._resolve_labels_from_ground_truth(features_data, ground_truth_path)

        known_idx = [i for i, l in enumerate(labels) if l not in holdout_labels]
        holdout_idx = [i for i, l in enumerate(labels) if l in holdout_labels]

        X_known = [features_data[i]["features"] for i in known_idx]
        y_known = [labels[i] for i in known_idx]

        X_holdout = [features_data[i]["features"] for i in holdout_idx]
        y_holdout = [labels[i] for i in holdout_idx]

        # Train anomaly detector ONLY on known data (never saw holdout labels)
        detector = IsolationForestAnomalyDetector(contamination=0.15, random_state=42)
        detector.fit(X_known)

        res = detector.evaluate_holdout(
            X_known=X_known,
            y_known=y_known,
            X_holdout=X_holdout if X_holdout else X_known,
            y_holdout=y_holdout if y_holdout else y_known,
            holdout_labels=holdout_labels,
        )

        self.db.save_model_metrics("holdout_experiment", res)
        return res
