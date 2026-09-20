"""Schema-mapping wizard backend: auto-detection of column synonyms, mapping overrides, and saved profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


CANONICAL_FIELDS = [
    "txid",
    "timestamp",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "input_addresses",
    "input_amounts",
    "output_addresses",
    "output_amounts",
    "fee",
    "script_type",
    "sensor_id",
]

# Comprehensive synonyms dictionary for auto-detection
FIELD_SYNONYMS: dict[str, list[str]] = {
    "txid": [
        "txid", "tx_id", "hash", "tx_hash", "transaction_id", "transaction_hash",
        "txhash", "tx_identifier", "id",
    ],
    "timestamp": [
        "timestamp", "ts", "time", "block_time", "first_seen", "seen_time",
        "datetime", "event_time", "observed_at", "obs_time",
    ],
    "src_ip": [
        "src_ip", "source_ip", "ip_src", "client_ip", "relay_ip", "origin_ip", "orig_ip",
        "srcip", "sender_ip", "peer_ip", "remote_ip",
    ],
    "dst_ip": [
        "dst_ip", "dest_ip", "destination_ip", "ip_dst", "sensor_ip", "node_ip",
        "dstip", "target_ip", "receiver_ip", "vantage_ip",
    ],
    "src_port": [
        "src_port", "source_port", "sport", "srcport", "client_port", "sender_port",
    ],
    "dst_port": [
        "dst_port", "dest_port", "dport", "dstport", "sensor_port", "target_port",
    ],
    "input_addresses": [
        "input_addresses", "input_addrs", "inputs", "vin_addresses", "from_addresses",
        "in_addresses", "in_addrs", "vin_addrs", "vin", "from_addrs", "sources",
    ],
    "input_amounts": [
        "input_amounts", "input_amts", "in_amounts", "vin_amounts", "vin_amts",
        "in_amts", "amounts_in", "input_values", "in_values",
    ],
    "output_addresses": [
        "output_addresses", "output_addrs", "outputs", "vout_addresses", "to_addresses",
        "out_addresses", "out_addrs", "vout_addrs", "vout", "to_addrs", "destinations",
    ],
    "output_amounts": [
        "output_amounts", "output_amts", "out_amounts", "vout_amounts", "vout_amts",
        "out_amts", "amounts_out", "output_values", "out_values",
    ],
    "fee": [
        "fee", "fee_sat", "fee_satoshis", "transaction_fee", "tx_fee", "fees",
        "mining_fee", "miner_fee",
    ],
    "script_type": [
        "script_type", "type", "script", "tx_type", "address_type", "output_type",
    ],
    "sensor_id": [
        "sensor_id", "sensor", "vantage_point", "vantage_id", "observer_id", "probe_id",
    ],
}


import difflib


def _normalize_key(key: str) -> str:
    """Normalize header key by lowercasing and removing punctuation."""
    return re.sub(r"[^a-z0-9]", "", key.lower())


@dataclass
class ColumnMappingMatch:
    source_column: str
    canonical_field: str
    confidence: float
    match_type: str  # "exact", "synonym", "fuzzy"


@dataclass
class SchemaMapper:
    """Infers and applies column mappings to convert arbitrary input formats to canonical schema."""

    mapping: dict[str, str] = field(default_factory=dict)  # source_col -> canonical_field
    confidence: dict[str, float] = field(default_factory=dict)  # source_col -> confidence float
    matches: list[ColumnMappingMatch] = field(default_factory=list)

    @classmethod
    def auto_detect(cls, headers: list[str]) -> SchemaMapper:
        """Infer canonical field mapping from input headers with confidence scores."""
        mapping: dict[str, str] = {}
        confidences: dict[str, float] = {}
        matches: list[ColumnMappingMatch] = []
        assigned_canonical: set[str] = set()
        assigned_sources: set[str] = set()

        norm_headers = {h: _normalize_key(h) for h in headers}

        # Pass 1: Exact matches on canonical field name
        for raw_h, norm_h in norm_headers.items():
            if raw_h in assigned_sources:
                continue
            for canonical in CANONICAL_FIELDS:
                if canonical in assigned_canonical:
                    continue
                if raw_h.lower() == canonical:
                    mapping[raw_h] = canonical
                    confidences[raw_h] = 1.0
                    matches.append(ColumnMappingMatch(raw_h, canonical, 1.0, "exact"))
                    assigned_canonical.add(canonical)
                    assigned_sources.add(raw_h)
                    break
                elif norm_h == _normalize_key(canonical):
                    mapping[raw_h] = canonical
                    confidences[raw_h] = 0.98
                    matches.append(ColumnMappingMatch(raw_h, canonical, 0.98, "exact"))
                    assigned_canonical.add(canonical)
                    assigned_sources.add(raw_h)
                    break

        # Pass 2: Synonym dictionary matches
        for canonical, syns in FIELD_SYNONYMS.items():
            if canonical in assigned_canonical:
                continue
            norm_syns = [_normalize_key(s) for s in syns]

            for raw_h, norm_h in norm_headers.items():
                if raw_h in assigned_sources:
                    continue
                if norm_h in norm_syns:
                    mapping[raw_h] = canonical
                    confidences[raw_h] = 0.95
                    matches.append(ColumnMappingMatch(raw_h, canonical, 0.95, "synonym"))
                    assigned_canonical.add(canonical)
                    assigned_sources.add(raw_h)
                    break

        # Pass 3: Fuzzy string matching for remaining headers
        unmapped_headers = [h for h in headers if h not in assigned_sources]
        available_canonicals = [c for c in CANONICAL_FIELDS if c not in assigned_canonical]

        for raw_h in unmapped_headers:
            norm_h = norm_headers[raw_h]
            if not norm_h:
                continue

            best_canonical: str | None = None
            best_score: float = 0.0

            for canonical in available_canonicals:
                if canonical in assigned_canonical:
                    continue
                # Compare against canonical name
                score = difflib.SequenceMatcher(None, norm_h, _normalize_key(canonical)).ratio()
                # Compare against synonyms of this canonical
                for syn in FIELD_SYNONYMS.get(canonical, []):
                    s_score = difflib.SequenceMatcher(None, norm_h, _normalize_key(syn)).ratio()
                    if s_score > score:
                        score = s_score

                if score > best_score:
                    best_score = score
                    best_canonical = canonical

            # Threshold for fuzzy match
            if best_canonical and best_score >= 0.70:
                rounded_conf = round(best_score, 2)
                mapping[raw_h] = best_canonical
                confidences[raw_h] = rounded_conf
                matches.append(ColumnMappingMatch(raw_h, best_canonical, rounded_conf, "fuzzy"))
                assigned_canonical.add(best_canonical)
                assigned_sources.add(raw_h)

        return cls(mapping=mapping, confidence=confidences, matches=matches)

    def apply(self, record: dict[str, Any]) -> dict[str, Any]:
        """Transform raw input record into canonical field names."""
        canonical_record: dict[str, Any] = {}
        for raw_k, val in record.items():
            canonical_field = self.mapping.get(raw_k, raw_k)
            canonical_record[canonical_field] = val
        return canonical_record

    def preview(self, sample_records: list[dict[str, Any]], n: int = 5) -> list[dict[str, Any]]:
        """Apply mapping to sample rows to generate a preview for user confirmation."""
        return [self.apply(row) for row in sample_records[:n]]
