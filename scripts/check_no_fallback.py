#!/usr/bin/env python3
"""CI check: Ensure zero numeric literal fallbacks exist in the frontend source code."""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Match patterns like: || 0, || 450, || 0.965, || 180, || 1.0, etc.
FALLBACK_REGEX = re.compile(r'\|\|\s*(?:[0-9]+(?:\.[0-9]+)?)\b')
# Match fallback literal objects with hardcoded metrics
HARDCODED_METRIC_REGEX = re.compile(r'(?:accuracy|f1_macro|f1_weighted|anomaly_mean|separation_delta)\s*:\s*[0-9]+(?:\.[0-9]+)?')


def check_frontend(src_dir: Path) -> int:
    if not src_dir.exists():
        print(f"Error: Frontend source directory {src_dir} does not exist.")
        return 1

    violations: list[tuple[Path, int, str]] = []

    for path in sorted(src_dir.rglob("*")):
        if path.suffix not in (".js", ".jsx", ".ts", ".tsx"):
            continue
        if "__tests__" in path.parts or ".test." in path.name or ".spec." in path.name:
            continue

        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for idx, line in enumerate(lines, start=1):
            # Ignore comments
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            if FALLBACK_REGEX.search(line) or HARDCODED_METRIC_REGEX.search(line):
                violations.append((path, idx, line.strip()))

    if violations:
        print("=" * 70)
        print("FAIL: Numeric literal fallbacks detected in frontend source code!")
        print("ChainSentinel v2 Rule 1: Every number must be computed at runtime or show explicit 'N/A' state.")
        print("=" * 70)
        for p, line_no, content in violations:
            rel = p.relative_to(src_dir.parent)
            print(f"  {rel}:{line_no} -> {content}")
        print("=" * 70)
        print(f"Total violations: {len(violations)}")
        return 1

    print("PASS: Zero numeric literal fallbacks found in frontend/src.")
    return 0


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    frontend_src = base_dir / "frontend" / "src"
    sys.exit(check_frontend(frontend_src))
