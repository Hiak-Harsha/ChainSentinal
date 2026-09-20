"""Supervised gradient-boosted multi-class classifier for Bitcoin laundering typologies."""

from __future__ import annotations

from pathlib import Path
import pickle
from typing import Any
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.preprocessing import LabelEncoder

from chainsentinel.features.extractor import FEATURE_NAMES


class SupervisedTypologyClassifier:
    """Multi-class gradient boosted decision tree classifier detecting T1–T9 and legitimate entities."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.feature_names = list(FEATURE_NAMES)
        self.encoder = LabelEncoder()
        self.model = HistGradientBoostingClassifier(
            loss="log_loss",
            learning_rate=0.08,
            max_iter=150,
            min_samples_leaf=2,
            random_state=random_state,
        )
        self.is_fitted = False
        self.classes_: list[str] = []
        self.feature_importances_: dict[str, float] = {}

    def _to_array(self, X: np.ndarray | list[dict[str, float]]) -> np.ndarray:
        """Convert list of feature dicts or numpy array to 2D numpy float32 matrix."""
        if isinstance(X, np.ndarray):
            return np.nan_to_num(X.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        
        arr = np.zeros((len(X), len(self.feature_names)), dtype=np.float32)
        for i, row in enumerate(X):
            for j, fn in enumerate(self.feature_names):
                val = row.get(fn, 0.0)
                arr[i, j] = float(val) if val is not None and not np.isnan(val) and not np.isinf(val) else 0.0
        return arr

    def fit(self, X: np.ndarray | list[dict[str, float]], y: list[str]) -> SupervisedTypologyClassifier:
        """Fit model on training features and class labels."""
        X_arr = self._to_array(X)
        y_encoded = self.encoder.fit_transform(y)
        self.classes_ = [str(c) for c in self.encoder.classes_]

        self.model.fit(X_arr, y_encoded)
        self.is_fitted = True

        # Approximate feature importances using feature variances and tree splits
        # Or compute permutation importance on training data
        self._compute_feature_importances(X_arr, y_encoded)
        return self

    def _compute_feature_importances(self, X_arr: np.ndarray, y_encoded: np.ndarray) -> None:
        """Compute relative feature importance scores."""
        # Simple fast permutation-based importance approximation
        baseline_score = accuracy_score(y_encoded, self.model.predict(X_arr))
        importances = {}
        rng = np.random.default_rng(self.random_state)
        for j, fn in enumerate(self.feature_names):
            X_perm = X_arr.copy()
            X_perm[:, j] = rng.permutation(X_perm[:, j])
            perm_score = accuracy_score(y_encoded, self.model.predict(X_perm))
            importances[fn] = max(0.0, float(baseline_score - perm_score))
        
        total = sum(importances.values())
        if total > 0:
            self.feature_importances_ = {k: v / total for k, v in importances.items()}
        else:
            self.feature_importances_ = {k: 1.0 / len(self.feature_names) for k in self.feature_names}

    def predict_proba(self, X: np.ndarray | list[dict[str, float]]) -> np.ndarray:
        """Return calibrated multi-class probabilities (N, K)."""
        if not self.is_fitted:
            raise RuntimeError("Model has not been fitted.")
        X_arr = self._to_array(X)
        return self.model.predict_proba(X_arr)

    def predict(self, X: np.ndarray | list[dict[str, float]]) -> list[str]:
        """Predict class name for each instance."""
        if not self.is_fitted:
            raise RuntimeError("Model has not been fitted.")
        X_arr = self._to_array(X)
        y_pred = self.model.predict(X_arr)
        return [str(c) for c in self.encoder.inverse_transform(y_pred)]

    def predict_top_k(
        self, X: np.ndarray | list[dict[str, float]], k: int = 3
    ) -> list[list[tuple[str, float]]]:
        """Return top-k predictions with calibrated confidence scores for each sample."""
        probs = self.predict_proba(X)
        results = []
        for p in probs:
            top_indices = np.argsort(p)[::-1][:k]
            results.append([(self.classes_[idx], float(p[idx])) for idx in top_indices])
        return results

    def evaluate(
        self, X_val: np.ndarray | list[dict[str, float]], y_val: list[str]
    ) -> dict[str, Any]:
        """Evaluate validation metrics."""
        y_pred = self.predict(X_val)
        y_val_str = [str(y) for y in y_val]

        acc = float(accuracy_score(y_val_str, y_pred))
        prec = float(precision_score(y_val_str, y_pred, average="macro", zero_division=0))
        rec = float(recall_score(y_val_str, y_pred, average="macro", zero_division=0))
        f1_mac = float(f1_score(y_val_str, y_pred, average="macro", zero_division=0))
        f1_wt = float(f1_score(y_val_str, y_pred, average="weighted", zero_division=0))

        return {
            "accuracy": acc,
            "precision_macro": prec,
            "recall_macro": rec,
            "f1_macro": f1_mac,
            "f1_weighted": f1_wt,
            "classes": self.classes_,
        }

    def save(self, file_path: str | Path) -> None:
        """Serialize model and metadata to disk."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "encoder": self.encoder,
                    "classes_": self.classes_,
                    "feature_names": self.feature_names,
                    "feature_importances_": self.feature_importances_,
                    "is_fitted": self.is_fitted,
                    "random_state": self.random_state,
                },
                f,
            )

    @classmethod
    def load(cls, file_path: str | Path) -> SupervisedTypologyClassifier:
        """Load serialized model from disk."""
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        obj = cls(random_state=data.get("random_state", 42))
        obj.model = data["model"]
        obj.encoder = data["encoder"]
        obj.classes_ = data["classes_"]
        obj.feature_names = data["feature_names"]
        obj.feature_importances_ = data["feature_importances_"]
        obj.is_fitted = data["is_fitted"]
        return obj
