"""Generator configuration dataclass."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PRESETS: dict[str, int] = {
    "50k": 50_000,
    "500k": 500_000,
    "2m": 2_000_000,
}


@dataclass
class GeneratorConfig:
    """Configuration for the synthetic data generator v2.

    All parameters that control data generation are centralized here
    for reproducibility. The config is serialized alongside output.
    """

    seed: int = 42
    total_tx: int = 100_000
    preset: str | None = None

    # Strict invariant: legit traffic share must be at least 90% and never zero
    min_legit_ratio: float = 0.90

    # Entity population (counts are scaled relative to total_tx)
    n_retail_users: int = 300
    n_merchants: int = 25
    n_exchange_hot: int = 8
    n_exchange_cold: int = 4
    n_payroll: int = 10
    n_mining_pools: int = 5
    n_gambling: int = 8
    n_custodial: int = 10

    # Illicit scenarios
    n_ransomware: int = 4
    n_darknet: int = 3
    n_peel_chain: int = 6
    n_coinjoin: int = 4
    n_layering: int = 4
    n_structuring: int = 4
    n_extortion: int = 3
    n_dusting: int = 3
    n_multi_cluster: int = 3

    # Network simulation
    n_sensors: int = 5
    n_relay_nodes: int = 200
    relay_mean_delay_s: float = 2.0
    gossip_mean_delay_s: float = 5.0

    # Obfuscation distribution (probabilities for levels 0-3)
    obfuscation_weights: list[float] = field(
        default_factory=lambda: [0.3, 0.3, 0.25, 0.15]
    )

    # Time range (Unix timestamps)
    start_timestamp: int = 1704067200  # 2024-01-01 00:00:00 UTC
    end_timestamp: int = 1711929600    # 2024-04-01 00:00:00 UTC

    # Output
    output_dir: str = "data/generated"
    formats: list[str] = field(default_factory=lambda: ["csv", "json", "xml"])

    def __post_init__(self) -> None:
        if self.preset:
            norm = self.preset.lower().strip()
            if norm in PRESETS:
                self.total_tx = PRESETS[norm]
            else:
                raise ValueError(f"Unknown preset '{self.preset}'. Supported: {list(PRESETS.keys())}")

    @property
    def illicit_ratio(self) -> float:
        """Approximate ratio of illicit transactions."""
        return 1.0 - self.min_legit_ratio

    @property
    def time_range_s(self) -> int:
        """Total time range in seconds."""
        return self.end_timestamp - self.start_timestamp

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to dict."""
        return asdict(self)

    def save(self, path: Path) -> None:
        """Save config to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeneratorConfig:
        """Load config from dict."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
