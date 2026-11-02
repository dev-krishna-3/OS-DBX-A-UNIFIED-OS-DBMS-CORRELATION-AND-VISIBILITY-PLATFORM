# OS-DBX Endpoint Forensic Collector Agent

A lightweight, silent digital forensics collector designed for enterprise incident investigation.

---

## Capabilities
- **Process Lifecycle Detection**: Detects process creation and termination in real time via `psutil`.
- **Filesystem Mutation Watchdog**: Detects file creation, modification, and deletion via `watchdog`.
- **Host Resource Telemetry**: Samples CPU %, RAM usage, Disk I/O, and Network I/O.
- **Resilient Offline Ring Buffer**: Automatically queues events in memory and retries if network connectivity to the central server drops.
- **Silent Boot Operation**: Runs as a silent background service on system boot without console popups.

---

## Zero-Prerequisite Standalone Mode (No Python Required)

For target PCs where Python and developer tools are **not installed**:
1. Copy `agent/bin/osdbx-agent.exe` (9.5 MB standalone binary) to a USB drive or download it onto the target PC.
2. Run directly from PowerShell or Command Prompt:
   ```cmd
   osdbx-agent.exe --server http://<SERVER_IP>:8000
   ```
   Or double-click `install-agent.bat` (it automatically detects `bin\osdbx-agent.exe` and skips Python dependency checks).
3. To build a fresh binary at any time, run:
   ```cmd
   build-agent-exe.bat
   ```

---

## 1-Minute Quick Start (With Python)

The API requires the unique credential issued when an owner enrolls a device. The current collector can send that value as `OSDBX_API_TOKEN`, but credential provisioning, protected storage, revocation UX, and the encrypted durable queue are not implemented end to end yet. Do not use a human administrator token for the agent; do not use this collector for a pilot yet.

### On Windows
1. **To Install & Start Collecting (Auto-start on Boot)**:
   ```cmd
   install-agent.bat
   ```
   *(Optionally pass server URL: `install-agent.bat https://your-server.com`)*

2. **To Cleanly Remove & Restore System**:
   ```cmd
   uninstall-agent.bat
   ```

### On macOS / Linux
1. **To Install & Start Collecting**:
   ```bash
   chmod +x install-agent.sh uninstall-agent.sh
   ./install-agent.sh
   ```

2. **To Cleanly Remove**:
   ```bash
   ./uninstall-agent.sh
   ```
