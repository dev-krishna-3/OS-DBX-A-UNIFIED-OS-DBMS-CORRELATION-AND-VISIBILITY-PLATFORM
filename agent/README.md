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

## 1-Minute Quick Start

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
