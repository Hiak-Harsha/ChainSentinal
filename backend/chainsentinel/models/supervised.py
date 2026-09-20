"""Supervised gradient-boosted multi-class classifier for Bitcoin laundering typologies."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
import lightgbm as lgb
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.preprocessing import LabelEncoder

from chainsentinel.features.extractor import FEATURE_NAMES


class SupervisedTypologyClassifier:
    """Multi-class gradient boosted decision tree classifier detecting T1–T9 and legitimate entities.
    
    Implements native LightGBM model format serialization with SHA-256 integrity checks
    and exact C++ TreeSHAP margins for explainability.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.feature_names = list(FEATURE_NAMES)
        self.encoder = LabelEncoder()
        self.booster: lgb.Booster | None = None
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
        """Fit model on training features and class labels using LightGBM."""
        X_arr = self._to_array(X)
        y_encoded = self.encoder.fit_transform(y)
        self.classes_ = [str(c) for c in self.encoder.classes_]

        num_classes = len(self.classes_)
        params = {
            "objective": "multiclass" if num_classes > 2 else "binary",
            "num_class": num_classes if num_classes > 2 else 1,
            "learning_rate": 0.08,
            "num_leaves": 31,
            "min_data_in_leaf": 2,
            "random_state": self.random_state,
            "verbose": -1,
            "n_jobs": 1,
        }

        train_data = lgb.Dataset(X_arr, label=y_encoded, free_raw_data=False)
        self.booster = lgb.train(
            params=params,
            train_set=train_data,
            num_boost_round=100,
        )
        self.is_fitted = True

        raw_imp = self.booster.feature_importance(importance_type="gain")
        total_imp = float(np.sum(raw_imp))
        if total_imp > 0:
            self.feature_importances_ = {
                fn: float(raw_imp[j] / total_imp) for j, fn in enumerate(self.feature_names)
            }
        else:
            self.feature_importances_ = {fn: 1.0 / len(self.feature_names) for fn in self.feature_names}

        return self

    def predict_proba(self, X: np.ndarray | list[dict[str, float]]) -> np.ndarray:
        """Return calibrated multi-class probabilities (N, K)."""
        if not self.is_fitted or self.booster is None:
            raise RuntimeError("Model has not been fitted.")
        X_arr = self._to_array(X)
        probs = self.booster.predict(X_arr)
        if len(self.classes_) == 2 and probs.ndim == 1:
            return np.column_stack([1.0 - probs, probs])
        return probs

    def predict(self, X: np.ndarray | list[dict[str, float]]) -> list[str]:
        """Predict class name for each instance."""
        probs = self.predict_proba(X)
        pred_idx = np.argmax(probs, axis=1)
        return [self.classes_[idx] for idx in pred_idx]

    def predict_raw(self, X: np.ndarray | list[dict[str, float]]) -> np.ndarray:
        """Return uncalibrated raw margins (scores before softmax)."""
        if not self.is_fitted or self.booster is None:
            raise RuntimeError("Model has not been fitted.")
        X_arr = self._to_array(X)
        return self.booster.predict(X_arr, raw_score=True)

    def predict_contribs(
        self, X: np.ndarray | list[dict[str, float]], class_idx: int | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute exact TreeSHAP feature contributions and base values.
        
        Returns:
            (shap_values, base_values) where shap_values is (N, num_features)
            and sum(shap_values, axis=1) + base_values equals the model raw margin.
        """
        if not self.is_fitted or self.booster is None:
            raise RuntimeError("Model has not been fitted.")
        X_arr = self._to_array(X)
        raw_contribs = self.booster.predict(X_arr, pred_contrib=True)

        num_feats = len(self.feature_names)
        num_classes = len(self.classes_)

        if num_classes <= 2:
            # Binary shape is (N, num_feats + 1)
            feats_shap = raw_contribs[:, :num_feats]
            base_val = raw_contribs[:, num_feats]
            return feats_shap, base_val

        # Multiclass shape is (N, (num_feats + 1) * num_classes)
        target_idx = class_idx if class_idx is not None else 0
        target_idx = min(max(0, target_idx), num_classes - 1)

        chunk_size = num_feats + 1
        class_chunk = raw_contribs[:, target_idx * chunk_size : (target_idx + 1) * chunk_size]
        feats_shap = class_chunk[:, :num_feats]
        base_val = class_chunk[:, num_feats]
        return feats_shap, base_val

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
        """Serialize model to LightGBM native text format with companion JSON metadata and SHA-256."""
        if not self.is_fitted or self.booster is None:
            raise RuntimeError("Cannot save unfitted model.")

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        model_file = path.with_suffix(".txt")
        meta_file = path.with_suffix(".json")

        self.booster.save_model(str(model_file))
        sha256_hash = hashlib.sha256(model_file.read_bytes()).hexdigest()

        meta = {
            "format": "lightgbm_native_v2",
            "model_file": model_file.name,
            "sha256": sha256_hash,
            "classes": self.classes_,
            "feature_names": self.feature_names,
            "feature_importances": self.feature_importances_,
            "random_state": self.random_state,
            "is_fitted": self.is_fitted,
        }
        meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, file_path: str | Path) -> SupervisedTypologyClassifier:
        """Load serialized LightGBM model verifying SHA-256 checksum."""
        path = Path(file_path)
        meta_file = path.with_suffix(".json")
        model_file = path.with_suffix(".txt")

        if not meta_file.exists():
            raise FileNotFoundError(f"Model metadata not found at {meta_file}")
        if not model_file.exists():
            raise FileNotFoundError(f"Native model file not found at {model_file}")

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        expected_hash = meta.get("sha256")
        actual_hash = hashlib.sha256(model_file.read_bytes()).hexdigest()

        if expected_hash != actual_hash:
            raise ValueError(
                f"Model integrity verification failed for {model_file}: "
                f"expected SHA-256 {expected_hash}, got {actual_hash}"
            )

        obj = cls(random_state=meta.get("random_state", 42))
        obj.classes_ = meta.get("classes", [])
        obj.feature_names = meta.get("feature_names", list(FEATURE_NAMES))
        obj.feature_importances_ = meta.get("feature_importances", {})
        obj.is_fitted = meta.get("is_fitted", True)
        obj.booster = lgb.Booster(model_file=str(model_file))

        # Reconstruct encoder classes
        obj.encoder = LabelEncoder()
        obj.encoder.classes_ = np.array(obj.classes_)
        return obj
