#!/bin/bash
# ChainSentinel — Forensic Intelligence Platform (NTRO SIH26146)
# Production Launch Script (Air-gapped single-port server)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "      ChainSentinel — Forensic Intelligence Platform      "
echo "  AI-Powered Monitoring of Bitcoin Transaction Traffic    "
echo "=========================================================="

VENV_DIR="$SCRIPT_DIR/backend/.venv"
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "[-] Error: Virtual environment not found. Please run ./install.sh first."
    exit 1
fi

source "$VENV_DIR/bin/activate"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo "[*] Starting ChainSentinel unified service..."
echo "[*] API Endpoint:       http://${HOST}:${PORT}/api/health"
echo "[*] Web Dashboard:      http://${HOST}:${PORT}/"
echo "[*] Interactive Docs:   http://${HOST}:${PORT}/docs"
echo "----------------------------------------------------------"
echo "[+] Press Ctrl+C to stop the service."
echo ""

cd "$SCRIPT_DIR/backend"
exec python -m uvicorn app.main:app --host "$HOST" --port "$PORT"
