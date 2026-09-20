#!/bin/bash
# ChainSentinel — Forensic Intelligence Platform (NTRO SIH26146)
# Offline / Linux Production Installer
# Target: Ubuntu 22.04 / 24.04 LTS, Debian 12, x86_64

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "      ChainSentinel — Offline Forensic Installer          "
echo "  AI-Powered Monitoring of Bitcoin Transaction Traffic    "
echo "=========================================================="

# Check Python version
PYTHON_CMD="python3"
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "[-] Error: python3 is not installed or not in PATH."
    exit 1
fi

PY_VER=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[+] Detected Python version: $PY_VER"

# Create Python virtual environment
VENV_DIR="$SCRIPT_DIR/backend/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[+] Creating Python virtual environment in $VENV_DIR..."
    $PYTHON_CMD -m venv "$VENV_DIR"
else
    echo "[*] Using existing virtual environment: $VENV_DIR"
fi

# Activate virtualenv
source "$VENV_DIR/bin/activate"

# Upgrade pip & install backend packages
echo "[+] Installing backend Python dependencies..."
if [ -d "$SCRIPT_DIR/wheelhouse" ]; then
    echo "[*] Installing from local wheelhouse (strict air-gap mode)..."
    pip install --no-index --find-links="$SCRIPT_DIR/wheelhouse" -e "$SCRIPT_DIR/backend"
else
    echo "[*] Installing Python packages from pyproject.toml..."
    pip install -e "$SCRIPT_DIR/backend"
fi

# Check Node.js and build frontend
if command -v npm &> /dev/null; then
    echo "[+] Building analyst dashboard frontend..."
    cd "$SCRIPT_DIR/frontend"
    if [ ! -d "node_modules" ]; then
        npm install --prefer-offline --no-audit
    fi
    npm run build
    cd "$SCRIPT_DIR"
    echo "[+] Frontend static production build compiled to frontend/out/"
else
    echo "[!] Warning: npm not found in PATH. Checking for existing frontend/out build..."
    if [ -d "$SCRIPT_DIR/frontend/out" ]; then
        echo "[*] Found pre-compiled frontend in frontend/out/"
    else
        echo "[-] Error: frontend/out does not exist and npm is not available to build it."
        exit 1
    fi
fi

# Initialize data directories
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$SCRIPT_DIR/docs"

echo ""
echo "=========================================================="
echo "[+] ChainSentinel installation completed successfully!"
echo "    To launch the platform, run:"
echo "    ./run.sh"
echo "=========================================================="
