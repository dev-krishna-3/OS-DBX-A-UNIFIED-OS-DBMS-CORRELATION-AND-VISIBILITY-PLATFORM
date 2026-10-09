from abc import ABC, abstractmethod
from typing import Optional
from .stream import LiveEventStream

class OSCollectorAdapter(ABC):
    """
    Cross-Platform OS Collector Adapter Interface.
    Defines the contract for OS-specific collectors (Linux, Windows, macOS).
    """
    
    def __init__(self, stream: LiveEventStream):
        self.stream = stream
        self.is_running = False

    @abstractmethod
    def start(self) -> None:
        """Starts OS event collection."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops OS event collection cleanly."""
        pass

    @abstractmethod
    def get_health(self) -> dict:
        """Returns the health status of the adapter and its collectors."""
        pass
