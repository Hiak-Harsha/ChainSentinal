"""Ingestion and validation engine for ChainSentinel."""

from __future__ import annotations

try:
    from chainsentinel.ingest.pipeline import IngestPipeline
    __all__ = ["IngestPipeline"]
except ImportError:
    __all__ = []

