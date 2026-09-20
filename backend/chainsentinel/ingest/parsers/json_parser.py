"""Streaming JSON and NDJSON parser."""

from __future__ import annotations

from collections.abc import Generator
import json
from pathlib import Path
from typing import Any

from chainsentinel.ingest.parsers.base import BaseStreamingParser


class JsonStreamingParser(BaseStreamingParser):
    """Streaming parser for NDJSON (newline-delimited JSON) and standard JSON files."""

    def __init__(self, file_path: str | Path, chunk_size: int = 10_000):
        super().__init__(file_path, chunk_size)
        self._headers: list[str] | None = None

    def get_headers(self) -> list[str]:
        if self._headers is not None:
            return self._headers

        with open(self.file_path, mode="r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("[") or line.startswith("]"):
                    continue
                try:
                    obj = json.loads(line.rstrip(","))
                    if isinstance(obj, dict):
                        self._headers = list(obj.keys())
                        return self._headers
                except Exception:
                    continue

        self._headers = []
        return self._headers

    def iter_chunks(self) -> Generator[list[dict[str, Any]], None, None]:
        with open(self.file_path, mode="r", encoding="utf-8", errors="replace") as f:
            chunk: list[dict[str, Any]] = []

            for line in f:
                line = line.strip()
                if not line or line == "[" or line == "]":
                    continue
                # Strip trailing comma if inside a JSON array
                if line.endswith(","):
                    line = line[:-1].strip()

                try:
                    record = json.loads(line)
                    if isinstance(record, dict):
                        chunk.append(record)
                except Exception:
                    # Ignore syntax artifact or partial line, validator will catch missing fields
                    continue

                if len(chunk) >= self.chunk_size:
                    yield chunk
                    chunk = []

            if chunk:
                yield chunk
