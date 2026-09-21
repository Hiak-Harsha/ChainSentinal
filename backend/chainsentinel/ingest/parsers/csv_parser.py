"""Streaming CSV parser with array unpacking and type conversion."""

from __future__ import annotations

from collections.abc import Generator
import csv
import json
import logging
from pathlib import Path
from typing import Any

from chainsentinel.ingest.parsers.base import BaseStreamingParser

logger = logging.getLogger("chainsentinel.ingest.csv_parser")


def _parse_csv_array(val: Any, is_int: bool = False) -> list[Any]:
    """Parse array value from semicolon string, JSON string, or native list."""
    if isinstance(val, (list, tuple)):
        return [int(x) if is_int else str(x) for x in val]
    if val is None or val == "":
        return []
    s = str(val).strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [int(x) if is_int else str(x) for x in parsed]
        except Exception as err:
            logger.debug("Failed to JSON parse array from CSV field '%s': %s", s, err)
    # Semicolon or comma separated
    parts = [p.strip() for p in s.split(";") if p.strip()]
    if not parts and "," in s:
        parts = [p.strip() for p in s.split(",") if p.strip()]
    if is_int:
        res = []
        for p in parts:
            try:
                res.append(int(p))
            except ValueError:
                pass
        return res
    return parts


class CsvStreamingParser(BaseStreamingParser):
    """Memory-bounded streaming CSV parser."""

    def __init__(self, file_path: str | Path, chunk_size: int = 10_000):
        super().__init__(file_path, chunk_size)
        self._headers: list[str] | None = None

    def get_headers(self) -> list[str]:
        if self._headers is None:
            with open(self.file_path, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                self._headers = next(reader, [])
        return self._headers

    def iter_chunks(self) -> Generator[list[dict[str, Any]], None, None]:
        with open(self.file_path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            self._headers = reader.fieldnames or []
            chunk: list[dict[str, Any]] = []

            for row in reader:
                parsed_row: dict[str, Any] = {}
                for k, v in row.items():
                    if k is None:
                        continue
                    k_lower = k.lower()
                    if "amounts" in k_lower or "amts" in k_lower or "values" in k_lower:
                        parsed_row[k] = _parse_csv_array(v, is_int=True)
                    elif "addresses" in k_lower or "addrs" in k_lower or "inputs" in k_lower or "outputs" in k_lower:
                        parsed_row[k] = _parse_csv_array(v, is_int=False)
                    else:
                        parsed_row[k] = v

                chunk.append(parsed_row)
                if len(chunk) >= self.chunk_size:
                    yield chunk
                    chunk = []

            if chunk:
                yield chunk
