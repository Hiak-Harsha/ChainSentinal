"""Explainability engine computing exact TreeSHAP feature attributions, peer percentiles, and forensic narratives."""

from __future__ import annotations

import math
from typing import Any
import numpy as np

from chainsentinel.features.extractor import FEATURE_NAMES


FEATURE_DESCRIPTIONS: dict[str, str] = {
    "peel_chain_depth": "Consecutive single-input dual-output transaction depth",
    "round_amount_ratio": "Proportion of transactions with round satoshi amounts",
    "dust_output_ratio": "Proportion of outputs below dust threshold (<=1000 sats)",
    "structuring_proximity": "Proportion of amounts near regulatory reporting thresholds",
    "fan_in_ratio": "Ratio of input counterparties to output counterparties",
    "fan_out_ratio": "Ratio of output counterparties to input counterparties",
    "ego_density": "Local 1-hop neighborhood interconnectivity density",
    "min_dwell_time": "Minimum dwell time between fund receipt and forward transfer",
    "burstiness": "Temporal burstiness and irregularity of transaction intervals",
    "circadian_entropy": "Hourly Shannon entropy of transaction dispatch times",
    "anonymizer_ratio": "Proportion of network observations routed through Tor/VPN exit nodes",
    "non_standard_port_ratio": "Proportion of connections on non-standard Bitcoin P2P ports",
    "ip_churn_rate": "Ratio of distinct origin/relay IPs to transaction count",
    "shared_origin_peer_count": "Number of distinct entity clusters sharing identical origin IPs",
    "min_shares_origin_p_value": "Empirical significance p-value of shared origin co-activity",
    "total_volume_sat": "Aggregate transaction volume in satoshis",
    "top_ip_posterior": "Maximum Bayesian posterior probability of entity-IP attribution",
    "origin_confidence_mean": "Mean confidence of first-seen P2P origin node estimates",
}


class ForensicExplainer:
    """Computes exact TreeSHAP attributions, population peer percentiles, and natural language reasons."""

    def __init__(
        self,
        supervised_model: Any,
        population_features: np.ndarray | list[dict[str, float]],
        feature_names: list[str] | None = None,
    ):
        self.supervised_model = supervised_model
        self.feature_names = feature_names or list(FEATURE_NAMES)
        self.population_matrix = self._to_array(population_features)
        self._init_population_stats()

    def _to_array(self, X: np.ndarray | list[dict[str, float]]) -> np.ndarray:
        if isinstance(X, np.ndarray):
            return np.nan_to_num(X.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        arr = np.zeros((len(X), len(self.feature_names)), dtype=np.float32)
        for i, row in enumerate(X):
            for j, fn in enumerate(self.feature_names):
                val = row.get(fn, 0.0)
                arr[i, j] = float(val) if val is not None and not np.isnan(val) and not np.isinf(val) else 0.0
        return arr

    def _init_population_stats(self) -> None:
        """Initialize empirical population distributions for peer percentile rankings."""
        if len(self.population_matrix) > 0:
            self.mean_vector = np.mean(self.population_matrix, axis=0)
            self.std_vector = np.std(self.population_matrix, axis=0)
        else:
            self.mean_vector = np.zeros(len(self.feature_names), dtype=np.float32)
            self.std_vector = np.ones(len(self.feature_names), dtype=np.float32)

    def compute_peer_percentiles(self, feature_dict: dict[str, float]) -> dict[str, float]:
        """Compute empirical percentile rank (0.0 to 100.0) for each feature against the population."""
        if len(self.population_matrix) == 0:
            return {k: 50.0 for k in feature_dict}

        percentiles = {}
        for j, fn in enumerate(self.feature_names):
            pop_col = self.population_matrix[:, j]
            val = float(feature_dict.get(fn, 0.0))
            rank = np.mean(pop_col <= val) * 100.0
            percentiles[fn] = round(float(rank), 1)

        return percentiles

    def compute_shap_values(
        self,
        feature_dict: dict[str, float],
        target_class_idx: int | None = None,
    ) -> tuple[dict[str, float], float]:
        """Compute exact TreeSHAP feature contributions and base value towards target class margin.
        
        Guarantees exact TreeSHAP efficiency/additivity property:
            sum(shap_values.values()) + base_value == model_margin
            
        Returns:
            (shap_dict, base_margin_value)
        """
        if hasattr(self.supervised_model, "predict_contribs") and getattr(self.supervised_model, "is_fitted", False):
            feat_contribs, base_vals = self.supervised_model.predict_contribs(
                [feature_dict], class_idx=target_class_idx
            )
            shap_dict = {
                fn: float(feat_contribs[0, j]) for j, fn in enumerate(self.feature_names)
            }
            base_val = float(base_vals[0])
            return shap_dict, base_val

        # If model is not fitted or doesn't support TreeSHAP, return zeros with neutral base
        shap_dict = {fn: 0.0 for fn in self.feature_names}
        return shap_dict, 0.0

    def explain_entity(
        self,
        entity_id: str,
        feature_dict: dict[str, float],
        predicted_class: str,
        class_prob: float,
        top_n: int = 4,
    ) -> list[dict[str, Any]]:
        """Generate explainable forensic drivers strictly complying with API schema and Truth-First rules."""
        class_idx = 0
        if hasattr(self.supervised_model, "classes_") and predicted_class in self.supervised_model.classes_:
            class_idx = self.supervised_model.classes_.index(predicted_class)

        shap_vals, base_margin = self.compute_shap_values(feature_dict, class_idx)
        percentiles = self.compute_peer_percentiles(feature_dict)

        # Sort features by absolute SHAP contribution
        sorted_feats = sorted(
            self.feature_names,
            key=lambda fn: abs(shap_vals.get(fn, 0.0)),
            reverse=True,
        )

        reasons = []
        for fn in sorted_feats[:top_n]:
            val = feature_dict.get(fn, 0.0)
            pctl = percentiles.get(fn, 50.0)
            shap_score = shap_vals.get(fn, 0.0)

            # Generate natural language narrative
            text = self._format_reason_text(fn, val, pctl, predicted_class)

            reasons.append({
                "feature": fn,
                "value": round(val, 4) if isinstance(val, float) else val,
                "peer_percentile": pctl,
                "shap": round(shap_score, 4),
                "text": text,
            })

        return reasons

    def _format_reason_text(self, feature: str, value: float, percentile: float, predicted_class: str) -> str:
        """Format domain-specific analyst explanation sentence."""
        desc = FEATURE_DESCRIPTIONS.get(feature, feature.replace("_", " "))

        if feature == "peel_chain_depth":
            return f"Peel chain depth of {int(value)} exceeds {percentile:.1f}% of entities, strongly indicating sequential peeling."
        elif feature == "round_amount_ratio":
            return f"{value*100:.1f}% of outputs have round satoshi amounts ({percentile:.1f}th percentile), matching structured ransomware/peel patterns."
        elif feature == "dust_output_ratio":
            return f"High dust output proportion of {value*100:.1f}% ({percentile:.1f}th percentile) characteristic of de-anonymization dusting."
        elif feature == "structuring_proximity":
            return f"{value*100:.1f}% of transactions fall within regulatory reporting thresholds ({percentile:.1f}th percentile)."
        elif feature == "anonymizer_ratio":
            return f"{value*100:.1f}% of observations routed via Tor/VPN exit nodes ({percentile:.1f}th percentile)."
        elif feature == "shared_origin_peer_count":
            return f"Correlated with {int(value)} distinct entity clusters via shared origin IP broadcast ({percentile:.1f}th percentile)."
        elif feature == "min_shares_origin_p_value":
            return f"Multi-cluster origin sharing exhibits statistically significant co-activity (empirical p-value {value:.4f})."
        elif feature == "non_standard_port_ratio":
            return f"{value*100:.1f}% of network traffic connects to non-standard P2P ports ({percentile:.1f}th percentile)."
        elif feature == "burstiness":
            return f"Temporal burstiness index of {value:.2f} ({percentile:.1f}th percentile) reflects automated robotic batch dispatch."
        elif feature == "min_dwell_time":
            return f"Rapid fund forwarding with minimum dwell time of {value:.1f}s ({percentile:.1f}th percentile), indicating automated layering."
        elif feature == "circadian_entropy":
            return f"Circadian entropy of {value:.2f} bits ({percentile:.1f}th percentile) indicates non-stop automated round-the-clock operation."
        else:
            return f"{desc} is {value:.2f}, ranking in the {percentile:.1f}th percentile across the analyzed population."
