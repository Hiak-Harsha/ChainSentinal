"""Inductive Conformal Prediction for mathematically grounded classification confidence bounds."""

from __future__ import annotations

import math
from pathlib import Path
import pickle
from typing import Any
import numpy as np


class ConformalPredictor:
    """Split conformal predictor producing guaranteed prediction sets and confidence grades."""

    def __init__(self, default_alpha: float = 0.10):
        self.default_alpha = default_alpha  # 0.10 -> 90% confidence guarantee
        self.classes_: list[str] = []
        self.nonconformity_scores_: np.ndarray = np.array([])
        self.is_calibrated = False

    def calibrate(
        self,
        probs_cal: np.ndarray,
        y_cal: list[str],
        classes: list[str],
    ) -> ConformalPredictor:
        """Calibrate non-conformity scores on a hold-out calibration split."""
        self.classes_ = list(classes)
        class_to_idx = {c: i for i, c in enumerate(self.classes_)}

        scores = []
        for i, true_label in enumerate(y_cal):
            if true_label in class_to_idx:
                c_idx = class_to_idx[true_label]
                # Non-conformity score: 1 - P(true_class)
                p_true = float(probs_cal[i, c_idx])
                scores.append(1.0 - p_true)
            else:
                scores.append(1.0)

        self.nonconformity_scores_ = np.sort(np.array(scores, dtype=np.float64))
        self.is_calibrated = True
        return self

    def get_threshold(self, alpha: float | None = None) -> float:
        """Compute conformal non-conformity quantile threshold for given error rate alpha."""
        if not self.is_calibrated or len(self.nonconformity_scores_) == 0:
            return 0.50

        sig = alpha if alpha is not None else self.default_alpha
        n = len(self.nonconformity_scores_)
        # Standard conformal quantile index: ceil((n + 1) * (1 - alpha)) / n
        q_idx = math.ceil((n + 1) * (1.0 - sig)) - 1
        q_idx = min(max(0, q_idx), n - 1)
        return float(self.nonconformity_scores_[q_idx])

    def predict_sets(
        self,
        probs: np.ndarray,
        alpha: float | None = None,
    ) -> list[dict[str, Any]]:
        """Compute conformal prediction set and reliability grade for each instance."""
        threshold = self.get_threshold(alpha)
        # Prediction set condition: P(class) >= 1.0 - threshold
        p_min = max(0.0, 1.0 - threshold)

        results = []
        for p in probs:
            top_idx = int(np.argmax(p))
            top_class = self.classes_[top_idx] if self.classes_ else "UNKNOWN"
            top_p = float(p[top_idx])

            # Classes that meet or exceed the conformal cutoff
            selected = [
                self.classes_[i]
                for i, prob_val in enumerate(p)
                if prob_val >= p_min and i < len(self.classes_)
            ]

            # Guarantee non-empty set by falling back to argmax
            if not selected:
                selected = [top_class]

            set_size = len(selected)

            # Assign reliability grade (A: High confidence singleton, B: Moderate set, C: High ambiguity)
            if set_size == 1 and top_p >= 0.80:
                grade = "A"
            elif set_size <= 2 and top_p >= 0.50:
                grade = "B"
            else:
                grade = "C"

            results.append({
                "conformal_set": selected,
                "set_size": set_size,
                "grade": grade,
                "calibrated_p": top_p,
                "top_class": top_class,
                "p_cutoff": p_min,
            })

        return results

    def save(self, file_path: str | Path) -> None:
        """Serialize conformal calibration data."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "default_alpha": self.default_alpha,
                    "classes_": self.classes_,
                    "nonconformity_scores_": self.nonconformity_scores_,
                    "is_calibrated": self.is_calibrated,
                },
                f,
            )

    @classmethod
    def load(cls, file_path: str | Path) -> ConformalPredictor:
        """Load serialized conformal predictor."""
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        obj = cls(default_alpha=data.get("default_alpha", 0.10))
        obj.classes_ = data["classes_"]
        obj.nonconformity_scores_ = data["nonconformity_scores_"]
        obj.is_calibrated = data["is_calibrated"]
        return obj
