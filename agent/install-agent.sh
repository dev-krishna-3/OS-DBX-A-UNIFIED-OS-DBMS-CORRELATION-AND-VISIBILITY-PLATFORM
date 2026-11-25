#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "      OS-DBX: Enterprise Endpoint Forensic Agent Installer (Unix)"
echo "======================================================================"
echo ""

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_URL="${1:-http://localhost:8000}"
DEVICE_TOKEN="${2:-}"
HOST_NAME="$(hostname)"

if [ -z "$DEVICE_TOKEN" ]; then
    read -r -p "Enter Device Credential Token (from OS-DBX Devices panel): " DEVICE_TOKEN
fi

echo "[*] Target Server: $SERVER_URL"
echo "[*] Target Host:   $HOST_NAME"

# 1. Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found. Please install Python 3.10+."
    exit 1
fi

# 2. Dependencies
echo "[*] Checking psutil & watchdog..."
python3 -m pip install --quiet psutil watchdog

# 3. Config
cat <<EOF > "$AGENT_DIR/config.json"
{
  "server_url": "$SERVER_URL",
  "host_id": "$HOST_NAME",
  "api_token": "$DEVICE_TOKEN",
  "watch_paths": ["$HOME/Desktop", "$AGENT_DIR"],
  "poll_interval_sec": 3.0
}
EOF

# 4. Auto-start on boot via user crontab
CRON_CMD="@reboot cd $AGENT_DIR && python3 osdbx_agent.py >> agent.log 2>&1"
(crontab -l 2>/dev/null | grep -v "osdbx_agent.py"; echo "$CRON_CMD") | crontab -

# 5. Launch immediately in background
nohup python3 "$AGENT_DIR/osdbx_agent.py" > "$AGENT_DIR/agent.log" 2>&1 &
echo $! > "$AGENT_DIR/agent.pid"

echo ""
echo "======================================================================"
echo " [✓] OS-DBX Forensic Collector successfully enrolled!"
echo " Endpoint Host ID: $HOST_NAME"
echo " Streaming To:     $SERVER_URL"
echo " Status:           Active (PID $(cat "$AGENT_DIR/agent.pid"))"
echo "======================================================================"
echo ""
