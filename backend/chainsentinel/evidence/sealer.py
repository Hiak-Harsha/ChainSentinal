"""Forensic evidence sealing, canonical serialization, and SHA-256 integrity verification.

Adheres to strict chain-of-custody requirements for court-admissible forensic case files.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any


def canonical_hash(data: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 digest over canonical sorted-key JSON representation."""
    serialized = json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def seal_evidence_bundle(bundle_data: dict[str, Any]) -> dict[str, Any]:
    """Seal an investigative evidence bundle with a canonical SHA-256 tamper-evident seal.
    
    Returns a sealed dictionary containing the bundle, its SHA-256 hash, and seal timestamp.
    """
    sealed_at = int(time.time())
    data_to_hash = dict(bundle_data)
    data_to_hash.pop("bundle_hash", None)
    data_to_hash.pop("sealed_at", None)

    digest = canonical_hash(data_to_hash)
    
    return {
        **bundle_data,
        "bundle_hash": digest,
        "sealed_at": sealed_at,
        "is_sealed": True,
    }


def verify_bundle_integrity(bundle_data: dict[str, Any], expected_hash: str | None = None) -> bool:
    """Verify that an evidence bundle has not been tampered with since sealing.
    
    If expected_hash is not supplied, uses bundle_data.get('bundle_hash').
    """
    target_hash = expected_hash or bundle_data.get("bundle_hash")
    if not target_hash:
        return False

    clean_bundle = {k: v for k, v in bundle_data.items() if k not in ("bundle_hash", "sealed_at", "is_sealed")}
    computed = canonical_hash(clean_bundle)
    return computed == target_hash
