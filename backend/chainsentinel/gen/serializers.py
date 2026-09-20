"""Serializers — write observation data to CSV, JSON (NDJSON), and XML.

All three formats contain identical logical data so they can be ingested
interchangeably during testing and demo.
"""

from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _flatten_observation(obs: dict[str, Any]) -> dict[str, Any]:
    """Flatten an observation record for CSV output.

    Arrays are joined with semicolons for CSV format.
    """
    flat = {}
    for key, value in obs.items():
        if isinstance(value, list):
            flat[key] = ";".join(str(v) for v in value)
        else:
            flat[key] = value
    return flat


def write_csv(observations: list[dict[str, Any]], path: Path) -> None:
    """Write observations to CSV file.

    Arrays are encoded as semicolon-separated strings.
    """
    if not observations:
        path.write_text("")
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    # Get all field names
    fieldnames = list(observations[0].keys())

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for obs in observations:
            writer.writerow(_flatten_observation(obs))


def write_json(observations: list[dict[str, Any]], path: Path) -> None:
    """Write observations to NDJSON (newline-delimited JSON) file.

    Arrays remain as native JSON arrays.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for obs in observations:
            f.write(json.dumps(obs, ensure_ascii=False, default=str))
            f.write("\n")


def write_xml(observations: list[dict[str, Any]], path: Path) -> None:
    """Write observations to XML file.

    Arrays are encoded as repeated child elements.
    Safe XML: no external entities, no DTD processing.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Stream-write to avoid building full tree in memory
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write("<observations>\n")

        for obs in observations:
            f.write("  <observation>\n")
            for key, value in obs.items():
                if isinstance(value, list):
                    f.write(f"    <{key}>\n")
                    for item in value:
                        f.write(f"      <item>{_xml_escape(str(item))}</item>\n")
                    f.write(f"    </{key}>\n")
                else:
                    f.write(f"    <{key}>{_xml_escape(str(value))}</{key}>\n")
            f.write("  </observation>\n")

        f.write("</observations>\n")


def _xml_escape(s: str) -> str:
    """Escape special XML characters."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def write_ground_truth(data: dict[str, Any], path: Path) -> None:
    """Write ground truth JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def write_config(data: dict[str, Any], path: Path) -> None:
    """Write generator config JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
