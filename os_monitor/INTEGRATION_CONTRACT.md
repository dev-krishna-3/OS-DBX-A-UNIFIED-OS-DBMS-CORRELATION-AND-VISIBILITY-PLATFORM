# Backend Integration Contract
*(For Person 4 - FastAPI/Integration Developer)*

This document outlines how the FastAPI backend integrates with the OS collector's Live Reality Mode.

## Core Buffer (`os_monitor.core.stream.os_event_stream`)
The OS events are actively buffered into a thread-safe singleton queue to gracefully handle event bursts.
Do not invoke collector scripts directly in HTTP handlers. Instead, spawn the `WindowsAdapter` as a background task, and `consume()` the stream.

### Starting the Collector (Lifecycle)
```python
from os_monitor.core.stream import os_event_stream
from os_monitor.adapters.windows_adapter import WindowsAdapter

# Initialize Adapter
adapter = WindowsAdapter(stream=os_event_stream, watch_paths=["C:\\Path\\To\\Watch"])

# On App Startup
adapter.start()

# On App Shutdown
adapter.stop()
```

### Consuming Events (Endpoint or Worker)
Extract normalized events continuously or via a batch REST endpoint:

```python
# Pull a single event safely
event = os_event_stream.consume(block=False)

if event:
    print(event.to_dict())
```

### Exposing OS Health & Benchmark Metrics
Your FastAPI `/health` or `/metrics` endpoint should expose:
1. `adapter.get_health()`
2. `os_event_stream.get_metrics()` (contains `events_received`, `events_processed`, `events_dropped`, `buffer_size`)
