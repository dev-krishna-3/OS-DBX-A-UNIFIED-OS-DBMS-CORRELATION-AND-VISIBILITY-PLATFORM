#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "         OS-DBX: Unified OS-DBMS Visibility Platform"
echo "======================================================================"
echo ""

# 1. Resolve root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH="$SCRIPT_DIR/backend:$SCRIPT_DIR/os_monitor"

# 2. Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.12+."
    exit 1
fi

# 3. Setup / Activate venv
if [ -f "$SCRIPT_DIR/backend/venv/bin/activate" ]; then
    echo "[*] Activating virtual environment..."
    source "$SCRIPT_DIR/backend/venv/bin/activate"
else
    echo "[*] Creating virtual environment in backend/venv..."
    python3 -m venv "$SCRIPT_DIR/backend/venv"
    source "$SCRIPT_DIR/backend/venv/bin/activate"
    echo "[*] Installing backend dependencies..."
    pip install -r "$SCRIPT_DIR/backend/requirements.txt"
fi

# 4. Check Frontend build
if [ ! -f "$SCRIPT_DIR/frontend/dist/index.html" ]; then
    echo "[*] Building frontend..."
    if command -v npm &>/dev/null; then
        cd "$SCRIPT_DIR/frontend"
        npm install
        npm run build
        cd "$SCRIPT_DIR"
    else
        echo "[!] npm not found. Serving API mode only."
    fi
fi

# 5. Open browser in background
(sleep 2 && (xdg-open "http://127.0.0.1:8000" 2>/dev/null || open "http://127.0.0.1:8000" 2>/dev/null || true)) &

echo ""
echo "======================================================================"
echo " [✓] OS-DBX Platform is running!"
echo " URL:   http://127.0.0.1:8000"
echo " API:   http://127.0.0.1:8000/docs"
echo " Admin account password is set with ADMIN_PASSWORD."
echo "======================================================================"
echo ""
echo "Press CTRL+C to stop the platform."
echo ""

python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
