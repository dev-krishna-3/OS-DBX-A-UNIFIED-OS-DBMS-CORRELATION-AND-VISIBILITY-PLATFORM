import queue
import logging
from typing import Optional
from .events import NormalizedOSEvent

class LiveEventStream:
    """
    Reliable stream/buffer for new OS events.
    Handles bursts safely without silently dropping events.
    """
    def __init__(self, max_size: int = 10000):
        self.buffer = queue.Queue(maxsize=max_size)
        self.events_received = 0
        self.events_processed = 0
        self.events_dropped = 0

    def publish(self, event: NormalizedOSEvent) -> bool:
        self.events_received += 1
        try:
            self.buffer.put_nowait(event)
            return True
        except queue.Full:
            self.events_dropped += 1
            logging.warning("OS Event stream buffer full. Event dropped.")
            return False

    def consume(self, block: bool = True, timeout: Optional[float] = None) -> Optional[NormalizedOSEvent]:
        try:
            event = self.buffer.get(block=block, timeout=timeout)
            self.events_processed += 1
            return event
        except queue.Empty:
            return None

    def get_metrics(self) -> dict:
        """
        Exposes stream counters for benchmark engine and real-time mode.
        """
        return {
            "events_received": self.events_received,
            "events_processed": self.events_processed,
            "events_dropped": self.events_dropped,
            "buffer_size": self.buffer.qsize()
        }

# Global singleton stream for the OS collector
os_event_stream = LiveEventStream()
