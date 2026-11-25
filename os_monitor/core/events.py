import uuid
import platform
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

def get_host_id() -> str:
    return platform.node()

@dataclass
class NormalizedOSEvent:
    event_type: str
    operation: str
    pid: Optional[int] = None
    process_name: Optional[str] = None
    file_path: Optional[str] = None
    resource_info: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Latency tracking fields (Phase 6 requirement)
    raw_capture_time: float = field(default_factory=time.time)
    normalization_time: Optional[float] = None
    
    # Auto-generated Identity Fields
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    source: str = "OS"
    host_id: str = field(default_factory=get_host_id)
    
    def __post_init__(self):
        # Set normalization time when the object finishes initialization
        self.normalization_time = time.time()
    
    @property
    def capture_latency_sec(self) -> float:
        return self.normalization_time - self.raw_capture_time

    @property
    def evidence_completeness(self) -> str:
        """
        Calculates Evidence Completeness (e.g., '4/5').
        Deterministic checks: pid, process_name, host_id, timestamp, and context (file/resource).
        """
        fields = [self.pid, self.process_name, self.host_id, self.timestamp]
        context_field = self.file_path or self.resource_info
        fields.append(context_field)
        
        available = sum(1 for f in fields if f is not None)
        total = len(fields)
        return f"{available}/{total}"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "event_type": self.event_type,
            "operation": self.operation,
            "pid": self.pid,
            "process_name": self.process_name,
            "file_path": self.file_path,
            "resource_info": self.resource_info,
            "metadata": self.metadata,
            "host_id": self.host_id,
            "evidence_completeness": self.evidence_completeness,
            "capture_latency_sec": self.capture_latency_sec
        }
