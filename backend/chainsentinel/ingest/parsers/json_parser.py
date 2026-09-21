"""Streaming JSON and NDJSON parser using ijson for JSON arrays and line-reader for NDJSON."""

from __future__ import annotations

from collections.abc import Generator
import json
import logging
from pathlib import Path
from typing import Any

try:
    import ijson
    HAS_IJSON = True
except ImportError:
    HAS_IJSON = False

from chainsentinel.ingest.parsers.base import BaseStreamingParser

logger = logging.getLogger("chainsentinel.ingest.json_parser")


class JsonStreamingParser(BaseStreamingParser):
    """Streaming parser for NDJSON (newline-delimited JSON) and standard JSON array files."""

    def __init__(self, file_path: str | Path, chunk_size: int = 10_000):
        super().__init__(file_path, chunk_size)
        self._headers: list[str] | None = None
        self._is_array: bool | None = None

    def _detect_format(self) -> bool:
        """Return True if JSON array, False if NDJSON."""
        if self._is_array is not None:
            return self._is_array
        with open(self.file_path, mode="rb") as f:
            while chunk := f.read(1024):
                stripped = chunk.strip()
                if stripped:
                    self._is_array = stripped.startswith(b"[")
                    return self._is_array
        self._is_array = False
        return self._is_array

    def get_headers(self) -> list[str]:
        if self._headers is not None:
            return self._headers

        for chunk in self.iter_chunks():
            if chunk:
                self._headers = list(chunk[0].keys())
                return self._headers
            break

        self._headers = []
        return self._headers

    def iter_chunks(self) -> Generator[list[dict[str, Any]], None, None]:
        is_array = self._detect_format()

        if is_array and HAS_IJSON:
            with open(self.file_path, mode="rb") as f:
                chunk: list[dict[str, Any]] = []
                for record in ijson.items(f, "item"):
                    if isinstance(record, dict):
                        chunk.append(record)
                    if len(chunk) >= self.chunk_size:
                        yield chunk
                        chunk = []
                if chunk:
                    yield chunk
            return

        # Fallback or NDJSON line-by-line streaming
        with open(self.file_path, mode="r", encoding="utf-8", errors="replace") as f:
            chunk: list[dict[str, Any]] = []

            for line in f:
                line = line.strip()
                if not line or line == "[" or line == "]":
                    continue
                if line.endswith(","):
                    line = line[:-1].strip()

                try:
                    record = json.loads(line)
                    if isinstance(record, dict):
                        chunk.append(record)
                except Exception as err:
                    logger.warning("Failed to parse JSON record in line-by-line fallback: %s (err: %s)", line[:80], err)
                    continue

                if len(chunk) >= self.chunk_size:
                    yield chunk
                    chunk = []

            if chunk:
                yield chunk
