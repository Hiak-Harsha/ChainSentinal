"""Base interface for streaming file parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from pathlib import Path
from typing import Any


class BaseStreamingParser(ABC):
    """Abstract base class for memory-bounded streaming data parsers."""

    def __init__(self, file_path: str | Path, chunk_size: int = 10_000):
        self.file_path = Path(file_path)
        self.chunk_size = chunk_size

    @abstractmethod
    def iter_chunks(self) -> Generator[list[dict[str, Any]], None, None]:
        """Yield batches of parsed raw observation records as dictionaries."""
        raise NotImplementedError

    @abstractmethod
    def get_headers(self) -> list[str]:
        """Return list of column/field names discovered in the file."""
        raise NotImplementedError

    def get_sample(self, n: int = 5) -> list[dict[str, Any]]:
        """Retrieve up to n parsed sample records for preview and mapping."""
        for chunk in self.iter_chunks():
            return chunk[:n]
        return []
