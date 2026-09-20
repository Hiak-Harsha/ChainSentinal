"""Data-Quality Report generator for ingested transaction datasets."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DataQualityReport:
    """Comprehensive quality metrics for an ingestion run."""

    total_rows_processed: int = 0
    valid_rows: int = 0
    quarantined_rows: int = 0
    duplicate_rows: int = 0
    unique_transactions: int = 0
    unique_addresses: int = 0
    unique_ips: int = 0
    completeness_scores: dict[str, float] = field(default_factory=dict)
    error_breakdown: dict[str, int] = field(default_factory=dict)
    anonymizer_count: int = 0
    total_volume_satoshis: int = 0
    total_fees_satoshis: int = 0
    duration_seconds: float = 0.0

    @property
    def valid_rate(self) -> float:
        if self.total_rows_processed == 0:
            return 0.0
        return self.valid_rows / self.total_rows_processed

    @property
    def duplicate_rate(self) -> float:
        if self.total_rows_processed == 0:
            return 0.0
        return self.duplicate_rows / self.total_rows_processed

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["valid_rate"] = round(self.valid_rate, 4)
        d["duplicate_rate"] = round(self.duplicate_rate, 4)
        return d
