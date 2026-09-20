"""Server-side registry for vetted datasets and ground-truth baselines."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import settings


def resolve_registered_ground_truth(dataset_name: str | None = None) -> Path:
    """Resolve ground truth path strictly from server-registered dataset names.

    Disallows arbitrary client-supplied filesystem paths to ensure security
    and reproducible evaluation.
    """
    cleaned = (dataset_name or "default").strip().lower()
    
    # Strictly reject path traversal or filesystem path injection attempts
    if "/" in cleaned or "\\" in cleaned or ".." in cleaned:
        raise ValueError(f"Invalid dataset name '{dataset_name}'. Client-supplied filesystem paths are prohibited.")

    registry: dict[str, Path] = {
        "default": settings.DATA_DIR / "cli_test" / "ground_truth.json",
        "cli_test": settings.DATA_DIR / "cli_test" / "ground_truth.json",
        "test_output_2": settings.DATA_DIR / "test_output_2" / "ground_truth.json",
        "test_output": settings.DATA_DIR / "test_output" / "ground_truth.json",
    }

    if cleaned in registry and registry[cleaned].exists():
        return registry[cleaned]

    # Search known candidate locations within server DATA_DIR
    for name, path in registry.items():
        if path.exists():
            return path

    fallback_root = Path(__file__).resolve().parents[2] / "data" / "cli_test" / "ground_truth.json"
    if fallback_root.exists():
        return fallback_root

    raise FileNotFoundError(f"Registered ground-truth dataset '{cleaned}' not found on server.")
