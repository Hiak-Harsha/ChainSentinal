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
    null_percentages: dict[str, float] = field(default_factory=dict)
    error_breakdown: dict[str, int] = field(default_factory=dict)
    value_distributions: dict[str, Any] = field(default_factory=dict)
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

    @property
    def quarantine_rate(self) -> float:
        if self.total_rows_processed == 0:
            return 0.0
        return self.quarantined_rows / self.total_rows_processed

    @property
    def throughput_rows_per_sec(self) -> float:
        if self.duration_seconds <= 0:
            return 0.0
        return round(self.total_rows_processed / self.duration_seconds, 1)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["valid_rate"] = round(self.valid_rate, 4)
        d["duplicate_rate"] = round(self.duplicate_rate, 4)
        d["quarantine_rate"] = round(self.quarantine_rate, 4)
        d["throughput_rows_per_sec"] = self.throughput_rows_per_sec
        return d
