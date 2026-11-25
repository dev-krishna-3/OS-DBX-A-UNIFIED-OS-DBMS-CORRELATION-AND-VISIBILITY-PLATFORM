"""osdbx.stream — re-exports EventStream (alias for LiveEventStream)."""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..'))
from os_monitor.core.stream import LiveEventStream as EventStream

__all__ = ["EventStream"]
