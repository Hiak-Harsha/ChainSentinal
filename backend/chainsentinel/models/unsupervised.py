"""Unsupervised anomaly detection using Isolation Forest for novel and unseen typologies."""

from __future__ import annotations

from pathlib import Path
import pickle
from typing import Any
import numpy as np
from sklearn.ensemble import IsolationForest

from chainsentinel.features.extractor import FEATURE_NAMES


class IsolationForestAnomalyDetector:
    """Detects novel, unseen, or high-risk anomalous behavior without requiring labeled examples."""

    def __init__(self, contamination: float = 0.15, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.feature_names = list(FEATURE_NAMES)
        self.model = IsolationForest(
            n_estimators=150,
            contamination=contamination,
            max_samples="auto",
            random_state=random_state,
        )
        self.is_fitted = False
        self.score_min_: float = 0.0
        self.score_max_: float = 1.0

    def _to_array(self, X: np.ndarray | list[dict[str, float]]) -> np.ndarray:
        if isinstance(X, np.ndarray):
            return np.nan_to_num(X.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        arr = np.zeros((len(X), len(self.feature_names)), dtype=np.float32)
        for i, row in enumerate(X):
            for j, fn in enumerate(self.feature_names):
                val = row.get(fn, 0.0)
                arr[i, j] = float(val) if val is not None and not np.isnan(val) and not np.isinf(val) else 0.0
        return arr

    def fit(self, X: np.ndarray | list[dict[str, float]]) -> IsolationForestAnomalyDetector:
        """Fit Isolation Forest on baseline or population feature vectors."""
        X_arr = self._to_array(X)
        self.model.fit(X_arr)
        self.is_fitted = True

        # Fit min/max calibration bounds on training decision function
        raw_scores = -self.model.decision_function(X_arr)
        self.score_min_ = float(np.min(raw_scores))
        self.score_max_ = float(np.max(raw_scores))
        if self.score_max_ <= self.score_min_:
            self.score_max_ = self.score_min_ + 1.0
        return self

    def score_samples(self, X: np.ndarray | list[dict[str, float]]) -> np.ndarray:
        """Compute normalized anomaly scores in [0.0, 1.0] where 1.0 is most anomalous."""
        if not self.is_fitted:
            raise RuntimeError("Anomaly detector has not been fitted.")
        X_arr = self._to_array(X)
        raw_scores = -self.model.decision_function(X_arr)
        # Min-max scale and clip to [0.0, 1.0]
        norm_scores = (raw_scores - self.score_min_) / (self.score_max_ - self.score_min_)
        return np.clip(norm_scores, 0.0, 1.0)

    def evaluate_holdout(
        self,
        X_known: np.ndarray | list[dict[str, float]],
        y_known: list[str],
        X_holdout: np.ndarray | list[dict[str, float]],
        y_holdout: list[str],
        holdout_labels: set[str],
    ) -> dict[str, Any]:
        """Evaluate how strongly unsupervised anomaly scores flag unseen hold-out typologies."""
        known_scores = self.score_samples(X_known)
        holdout_scores = self.score_samples(X_holdout)

        # Baseline legitimate vs holdout illicit anomaly scores
        legit_indices = [i for i, label in enumerate(y_known) if label.upper() == "LEGITIMATE"]
        legit_scores = known_scores[legit_indices] if legit_indices else known_scores

        holdout_indices = [i for i, label in enumerate(y_holdout) if label in holdout_labels]
        target_holdout_scores = holdout_scores[holdout_indices] if holdout_indices else holdout_scores

        legit_mean = float(np.mean(legit_scores)) if len(legit_scores) > 0 else 0.0
        holdout_mean = float(np.mean(target_holdout_scores)) if len(target_holdout_scores) > 0 else 0.0
        separation = holdout_mean - legit_mean

        return {
            "legitimate_anomaly_mean": legit_mean,
            "holdout_anomaly_mean": holdout_mean,
            "anomaly_separation_delta": separation,
            "holdout_count": len(target_holdout_scores),
            "flagged_as_anomalous_ratio": float(np.mean(target_holdout_scores > 0.5)) if len(target_holdout_scores) > 0 else 0.0,
        }

    def save(self, file_path: str | Path) -> None:
        """Serialize model to disk."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "contamination": self.contamination,
                    "random_state": self.random_state,
                    "score_min_": self.score_min_,
                    "score_max_": self.score_max_,
                    "is_fitted": self.is_fitted,
                    "feature_names": self.feature_names,
                },
                f,
            )

    @classmethod
    def load(cls, file_path: str | Path) -> IsolationForestAnomalyDetector:
        """Load serialized model from disk."""
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        obj = cls(
            contamination=data.get("contamination", 0.15),
            random_state=data.get("random_state", 42),
        )
        obj.model = data["model"]
        obj.score_min_ = data["score_min_"]
        obj.score_max_ = data["score_max_"]
        obj.is_fitted = data["is_fitted"]
        obj.feature_names = data["feature_names"]
        return obj
