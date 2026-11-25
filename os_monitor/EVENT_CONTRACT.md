# Normalized OS Event Contract
*(For Person 2 - DBMS Developer)*

This document defines the strict normalized event schema that the OS side guarantees for correlation.

## Event Shape
All OS events produced by the `LiveEventStream` will adhere to this flat, deterministic JSON structure:

```json
{
  "event_id": "uuid-v4-string",
  "timestamp": 1699999999.123,
  "source": "OS",
  "event_type": "process_created | file_modified | resource_usage | ...",
  "operation": "start | write | metric | ...",
  "pid": 1234,
  "process_name": "chrome.exe",
  "file_path": "C:\\path\\if\\applicable.txt",
  "resource_info": {"cpu_usage": 12.5, "memory_usage": 1.2, "disk_io": 1024, "network_io": null},
  "metadata": {"ppid": 1233, "is_directory": false},
  "host_id": "desktop-machine-name",
  "evidence_completeness": "4/5",
  "capture_latency_sec": 0.0001
}
```

## Critical Rules for Correlation Engine (Person 2)
1. **PID=null for Filesystem Events**: Due to OS constraints (without eBPF/auditd), filesystem modifications via `watchdog` will have `pid=null`. Correlation must rely on time-windowing and expected `file_path` access rather than strict PID equivalence.
2. **PID Recycling**: PIDs are recycled by the OS. A strict correlation rule *must* verify that the `timestamp` falls within the process's observed start and stop times.
3. **Evidence Completeness**: `evidence_completeness` provides a fraction representing how many deterministic fields are available (e.g. `pid`, `process_name`, `host_id`, `timestamp`, `file_path`/`resource_info`). Use this to weigh your correlation strength (e.g., 4/5). It is NOT probabilistic.
