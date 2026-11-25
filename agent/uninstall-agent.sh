#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "     OS-DBX: Enterprise Endpoint Forensic Agent Uninstaller (Unix)"
echo "======================================================================"
echo ""

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Kill PID if exists
if [ -f "$AGENT_DIR/agent.pid" ]; then
    PID="$(cat "$AGENT_DIR/agent.pid")"
    echo "[*] Stopping background agent (PID $PID)..."
    kill "$PID" 2>/dev/null || true
    rm -f "$AGENT_DIR/agent.pid"
fi

# 2. Kill by process name
pkill -f "osdbx_agent.py" 2>/dev/null || true

# 3. Remove crontab entry
crontab -l 2>/dev/null | grep -v "osdbx_agent.py" | crontab - 2>/dev/null || true

# 4. Clean logs
rm -f "$AGENT_DIR/agent.log"

echo ""
echo "======================================================================"
echo " [✓] OS-DBX Forensic Collector completely removed!"
echo " - Background daemon killed"
echo " - Boot autostart purged"
echo " - Zero system footprint remaining"
echo "======================================================================"
echo ""
