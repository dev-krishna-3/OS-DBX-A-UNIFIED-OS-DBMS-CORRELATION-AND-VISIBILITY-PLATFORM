"""osdbx.adapters — re-exports WindowsAdapter from os_monitor."""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..'))
from os_monitor.adapters.windows_adapter import WindowsAdapter

__all__ = ["WindowsAdapter"]
