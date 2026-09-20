"""Streaming XML parser using iterparse for bounded O(1) memory usage."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

try:
    import defusedxml.ElementTree as SafeET
    from defusedxml.common import DefusedXmlException, DTDForbidden, EntitiesForbidden
    HAS_DEFUSEDXML = True
except ImportError:
    import xml.etree.ElementTree as SafeET
    class DefusedXmlException(Exception): pass
    class DTDForbidden(DefusedXmlException): pass
    class EntitiesForbidden(DefusedXmlException): pass
    HAS_DEFUSEDXML = False

from chainsentinel.ingest.parsers.base import BaseStreamingParser


def _parse_xml_element(elem: ET.Element) -> dict[str, Any]:
    """Convert an <observation> XML element and its children to a dict."""
    record: dict[str, Any] = {}
    for child in elem:
        tag = child.tag
        sub_children = list(child)
        if sub_children:
            # Container of items, e.g. <input_addresses><address>...
            vals = []
            for sub in sub_children:
                text = (sub.text or "").strip()
                if "amount" in sub.tag or "amount" in tag:
                    try:
                        vals.append(int(text))
                    except ValueError:
                        vals.append(text)
                else:
                    vals.append(text)
            record[tag] = vals
        else:
            text = (child.text or "").strip()
            # Try parsing integer/float if applicable
            if tag in ("src_port", "dst_port", "fee"):
                try:
                    record[tag] = int(text)
                except ValueError:
                    record[tag] = text
            elif tag in ("timestamp", "ts"):
                try:
                    record[tag] = float(text)
                except ValueError:
                    record[tag] = text
            else:
                record[tag] = text
    return record


class XmlStreamingParser(BaseStreamingParser):
    """Memory-bounded streaming XML parser."""

    def __init__(self, file_path: str | Path, chunk_size: int = 10_000):
        super().__init__(file_path, chunk_size)
        self._headers: list[str] | None = None

    def get_headers(self) -> list[str]:
        if self._headers is not None:
            return self._headers

        try:
            context = SafeET.iterparse(str(self.file_path), events=("end",))
            for _, elem in context:
                if elem.tag.lower() in ("observation", "record"):
                    record = _parse_xml_element(elem)
                    self._headers = list(record.keys())
                    elem.clear()
                    break
        except (DefusedXmlException, DTDForbidden, EntitiesForbidden) as e:
            raise ValueError(f"Safe XML violation (XXE/DTD forbidden): {e}") from e
        return self._headers or []

    def iter_chunks(self) -> Generator[list[dict[str, Any]], None, None]:
        try:
            context = SafeET.iterparse(str(self.file_path), events=("end",))
            chunk: list[dict[str, Any]] = []

            for _, elem in context:
                tag_lower = elem.tag.lower()
                if tag_lower in ("observation", "record"):
                    record = _parse_xml_element(elem)
                    chunk.append(record)
                    elem.clear()

                    if len(chunk) >= self.chunk_size:
                        yield chunk
                        chunk = []

            if chunk:
                yield chunk
        except (DefusedXmlException, DTDForbidden, EntitiesForbidden) as e:
            raise ValueError(f"Safe XML violation (XXE/DTD forbidden): {e}") from e
