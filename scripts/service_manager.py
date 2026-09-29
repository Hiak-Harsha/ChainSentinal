"""ChainSentinel Windows Production Service Manager.

Provides robust start, stop, and status management for detached background deployment.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
DATA_DIR = ROOT_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
PID_FILE = DATA_DIR / "chainsentinel.pid"
STDOUT_LOG = LOG_DIR / "chainsentinel_stdout.log"
STDERR_LOG = LOG_DIR / "chainsentinel_stderr.log"

PYTHON_EXE = sys.executable


def get_stored_pid() -> int | None:
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            return None
    return None


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in res.stdout
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def stop_service() -> bool:
    pid = get_stored_pid()
    stopped = False
    if pid and is_pid_running(pid):
        print(f"[*] Stopping ChainSentinel service (PID: {pid})...")
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)
        else:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        time.sleep(1)
        stopped = True
    else:
        print("[*] No active service PID found in registry.")

    # Free port 8000 if occupied
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in res.stdout.splitlines():
                if ':8000' in line and 'LISTENING' in line:
                    parts = line.strip().split()
                    rogue_pid = parts[-1]
                    if rogue_pid.isdigit() and int(rogue_pid) > 4:
                        print(f"[*] Freeing port 8000 held by PID {rogue_pid}...")
                        subprocess.run(['taskkill', '/F', '/T', '/PID', rogue_pid], capture_output=True, check=False)
        except Exception:
            pass

    if PID_FILE.exists():
        try:
            PID_FILE.unlink()
        except OSError:
            pass

    print("[+] Service stopped.")
    return stopped


def start_service(host: str = "0.0.0.0", port: int = 8000) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "audit").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "uploads").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "models").mkdir(parents=True, exist_ok=True)

    stop_service()

    # Verify frontend build exists
    index_html = ROOT_DIR / "frontend" / "out" / "index.html"
    if not index_html.exists():
        print("[+] Compiling frontend production bundle...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        subprocess.run([npm_cmd, "run", "build"], cwd=ROOT_DIR / "frontend", check=True)

    cmd = [
        PYTHON_EXE,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    print(f"[+] Launching production daemon on http://{host}:{port}...")

    stdout_f = open(STDOUT_LOG, "a", encoding="utf-8")
    stderr_f = open(STDERR_LOG, "a", encoding="utf-8")

    creation_flags = 0
    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        creation_flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        cmd,
        cwd=BACKEND_DIR,
        stdout=stdout_f,
        stderr=stderr_f,
        creationflags=creation_flags,
        close_fds=(sys.platform != "win32"),
    )

    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    print(f"[*] Detached process initiated with PID: {proc.pid}")

    # Probe health
    health_url = f"http://127.0.0.1:{port}/api/health"
    healthy = False
    for _ in range(15):
        time.sleep(1)
        try:
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    healthy = True
                    break
        except Exception:
            pass

    if healthy:
        print("\n==========================================================")
        print("  DEPLOYMENT SUCCESSFUL -- SERVICE IS HEALTHY AND ONLINE  ")
        print("==========================================================")
        print(f"  Web Dashboard:      http://127.0.0.1:{port}/")
        print(f"  REST API Health:    http://127.0.0.1:{port}/api/health")
        print(f"  OpenAPI Docs:       http://127.0.0.1:{port}/api/docs")
        print(f"  WebSocket Stream:   ws://127.0.0.1:{port}/api/ws/telemetry")
        print(f"  Daemon PID:         {proc.pid}")
        print(f"  Service Log:        {STDERR_LOG}")
        print("----------------------------------------------------------")
        print("  Status command:     python scripts/service_manager.py status")
        print("  Stop command:       python scripts/service_manager.py stop")
        print("==========================================================\n")
    else:
        print(f"[!] Warning: Health probe timed out. Check log at: {STDERR_LOG}")
        sys.exit(1)


def status_service(port: int = 8000) -> None:
    pid = get_stored_pid()
    running = False
    if pid and is_pid_running(pid):
        running = True
        print(f"Daemon Status:       ONLINE (PID: {pid})")
    else:
        print("Daemon Status:       STOPPED / OFFLINE")

    if running:
        health_url = f"http://127.0.0.1:{port}/api/health"
        try:
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                print(f"Health Probe:        HTTP {resp.status} OK")
        except Exception as exc:
            print(f"Health Probe:        FAILED ({exc})")

    print(f"Log File:            {STDERR_LOG}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ChainSentinel Service Manager")
    parser.add_argument("action", choices=["start", "stop", "status", "restart"], help="Action to perform")
    parser.add_argument("--host", default="0.0.0.0", help="Binding host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")

    args = parser.parse_args()

    if args.action == "start":
        start_service(host=args.host, port=args.port)
    elif args.action == "stop":
        stop_service()
    elif args.action == "status":
        status_service(port=args.port)
    elif args.action == "restart":
        stop_service()
        time.sleep(1)
        start_service(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
