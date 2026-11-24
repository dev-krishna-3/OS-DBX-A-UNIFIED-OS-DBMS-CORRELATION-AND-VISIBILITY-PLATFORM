======================================================================
  OS-DBX Forensic Collector (Option 1: Standalone Executable)
======================================================================

How to Run:
1. Double-click "osdbx-agent.exe" (or "Run-Agent.bat").
2. The agent automatically detects this PC's hostname (e.g. LAPTOP-GP6CB324).
3. Live process creation, termination, and filesystem telemetry will stream to:
   https://testing-sooty-omega.vercel.app/

Configuration (agent_config.json):
- server_url: https://testing-4bux.onrender.com
- host_id: (empty by default, automatically captures computer name)
- api_token: 8xC_xZOr4QpFe0c0ZV1ZD2nwT03FzbHlME166yPU6ULSqyyDtcJo6mc7gv8ADcXx

Windows 11 Smart App Control Note:
If Windows 11 displays "Smart App Control blocked an app that may be unsafe":
- Microsoft requires an annual commercial EV certificate for standalone binaries.
- To run this standalone binary on Windows 11, set Smart App Control to Evaluation or Off in Windows Security settings.
- Alternatively, use Option 2 (Portable Runner), which runs on Microsoft's signed Python runtime with zero security prompts.
