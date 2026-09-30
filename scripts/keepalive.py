#!/usr/bin/env python3
"""ChainSentinel Render Backend Keep-Alive Trigger Script.

Pings the Render backend health endpoint periodically (default every 12 minutes)
to prevent the free-tier service from entering inactivity sleep.

Usage:
    python scripts/keepalive.py --url https://chainsentinel.onrender.com
    python scripts/keepalive.py --url https://chainsentinel.onrender.com --interval 12
    python scripts/keepalive.py --once
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
import sys
import time
import urllib.error
import urllib.request


def ping(url: str, timeout_sec: int = 60) -> bool:
    """Send an HTTP GET request to the health endpoint."""
    target = url.rstrip("/")
    if not target.endswith("/api/health"):
        if target.endswith("/api"):
            target = f"{target}/health"
        else:
            target = f"{target}/api/health"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] Pinging {target} ...", flush=True)

    try:
        req = urllib.request.Request(
            target,
            headers={
                "User-Agent": "ChainSentinel-KeepAlive/1.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"[{ts}] Status: {resp.status} OK | Response: {body.strip()[:120]}", flush=True)
            return resp.status == 200
    except urllib.error.HTTPError as e:
        print(f"[{ts}] HTTP Error {e.code}: {e.reason}", flush=True)
        return False
    except urllib.error.URLError as e:
        print(f"[{ts}] Network / Connection Error (Backend may be spinning up): {e.reason}", flush=True)
        return False
    except Exception as e:
        print(f"[{ts}] Ping Error: {e}", flush=True)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="ChainSentinel Render Keep-Alive Trigger")
    parser.add_argument(
        "--url",
        default=os.getenv("RENDER_BACKEND_URL", "https://chainsentinel.onrender.com"),
        help="Backend base URL or health endpoint URL",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=12,
        help="Ping interval in minutes (default: 12 mins, must be < 15 to prevent sleep)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds (default: 60s for cold-start tolerance)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Send a single ping and exit",
    )
    args = parser.parse_args()

    if args.once:
        success = ping(args.url, timeout_sec=args.timeout)
        sys.exit(0 if success else 1)

    interval_sec = max(60, args.interval * 60)
    print(
        f"ChainSentinel Keep-Alive Service started.\n"
        f"Target: {args.url}\n"
        f"Interval: {args.interval} minutes ({interval_sec}s)\n"
        f"Press Ctrl+C to stop.\n"
    )

    try:
        while True:
            ping(args.url, timeout_sec=args.timeout)
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        print("\nKeep-Alive service stopped.")


if __name__ == "__main__":
    main()
