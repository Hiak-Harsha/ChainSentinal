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
        "src_ip", "source_ip", "ip_src", "client_ip", "relay_ip", "origin_ip",
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


def _normalize_key(key: str) -> str:
    """Normalize header key by lowercasing and removing punctuation."""
    return re.sub(r"[^a-z0-9]", "", key.lower())


@dataclass
class SchemaMapper:
    """Infers and applies column mappings to convert arbitrary input formats to canonical schema."""

    mapping: dict[str, str] = field(default_factory=dict)  # source_col -> canonical_field

    @classmethod
    def auto_detect(cls, headers: list[str]) -> SchemaMapper:
        """Infer canonical field mapping from input headers."""
        mapping: dict[str, str] = {}
        assigned_canonical: set[str] = set()

        norm_headers = {h: _normalize_key(h) for h in headers}

        # First pass: check direct and synonyms matches
        for canonical, syns in FIELD_SYNONYMS.items():
            norm_syns = [_normalize_key(s) for s in syns]
            best_match: str | None = None

            for raw_h, norm_h in norm_headers.items():
                if norm_h in norm_syns and canonical not in assigned_canonical:
                    best_match = raw_h
                    break

            if best_match is not None:
                mapping[best_match] = canonical
                assigned_canonical.add(canonical)

        return cls(mapping=mapping)

    def apply(self, record: dict[str, Any]) -> dict[str, Any]:
        """Transform raw input record into canonical field names."""
        canonical_record: dict[str, Any] = {}
        for raw_k, val in record.items():
            canonical_field = self.mapping.get(raw_k, raw_k)
            canonical_record[canonical_field] = val
        return canonical_record
