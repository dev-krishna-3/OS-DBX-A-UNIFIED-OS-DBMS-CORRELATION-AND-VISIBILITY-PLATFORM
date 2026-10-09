import os
import time
import requests
import logging
from .core.stream import os_event_stream
from .adapters.windows_adapter import WindowsAdapter

# Configuration
BACKEND_URL = os.environ.get("OSDBX_BACKEND_URL")
WATCH_PATHS = ["."] # Currently watching the os_monitor directory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def start_collector():
    adapter = WindowsAdapter(stream=os_event_stream, watch_paths=WATCH_PATHS)
    adapter.start()
    logging.info(f"OS Collector started. Watching paths: {WATCH_PATHS}")
    
    if BACKEND_URL:
        logging.info(f"Connected to backend. Will POST events to {BACKEND_URL}/api/events")
    else:
        logging.info("No OSDBX_BACKEND_URL set. Running in local-only mode (printing events).")

    try:
        while True:
            # Safely consume events from the burst-safe buffer
            event = os_event_stream.consume(block=True, timeout=1.0)
            if not event:
                continue
                
            payload = event.to_dict()
            
            if BACKEND_URL:
                try:
                    res = requests.post(f"{BACKEND_URL}/api/events", json=payload, timeout=2.0)
                    if res.status_code not in (200, 201):
                        logging.warning(f"Backend rejected event: {res.status_code} - {res.text}")
                    else:
                        logging.info(f"Successfully posted {payload['event_type']} to backend.")
                except requests.exceptions.RequestException as e:
                    logging.error(f"Failed to post event to backend: {e}")
            else:
                # Local logging mode
                logging.info(f"Captured Event: {payload['event_type']} (PID: {payload['pid']})")
                
    except KeyboardInterrupt:
        logging.info("Shutting down collector...")
        adapter.stop()
        logging.info("Collector stopped safely.")

if __name__ == "__main__":
    start_collector()
