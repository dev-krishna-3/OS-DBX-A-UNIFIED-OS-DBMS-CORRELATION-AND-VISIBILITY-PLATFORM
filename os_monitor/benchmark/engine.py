import time
import psutil
import os
from typing import Dict, Any
from ..core.stream import LiveEventStream
from ..adapters.windows_adapter import WindowsAdapter
from .scenarios import OSBenchmarkScenario

class OSBenchmarkEngine:
    """
    OS-side benchmark metrics engine.
    Separates SYSTEM WORKLOAD from OS-DBX OBSERVABILITY OVERHEAD.
    Tracks capture latency and normalization latency.
    """
    def __init__(self, stream: LiveEventStream, adapter: WindowsAdapter):
        self.stream = stream
        self.adapter = adapter

    def run_scenario(self, scenario: OSBenchmarkScenario) -> Dict[str, Any]:
        process = psutil.Process(os.getpid())
        
        # Baseline Observability Overhead
        base_cpu = process.cpu_percent(interval=0.1)
        base_mem = process.memory_info().rss
        
        start_metrics = self.stream.get_metrics()
        
        was_running = self.adapter.is_running
        if not was_running:
            self.adapter.start()
            
        time.sleep(1)
        
        # Execute SYSTEM WORKLOAD
        scenario_results = scenario.execute()
        
        time.sleep(3)
        
        end_metrics = self.stream.get_metrics()
        
        if not was_running:
            self.adapter.stop()
            
        # Final Overhead
        peak_cpu = process.cpu_percent(interval=0.1)
        peak_mem = process.memory_info().rss
        
        events_generated = scenario_results["operation_count"]
        events_captured = end_metrics["events_received"] - start_metrics["events_received"]
        events_dropped = end_metrics["events_dropped"] - start_metrics["events_dropped"]
        
        # Calculate Latencies
        total_latency = 0.0
        processed = 0
        while True:
            ev = self.stream.consume(block=False)
            if not ev: break
            total_latency += ev.capture_latency_sec
            processed += 1
            
        avg_latency = (total_latency / processed) if processed > 0 else 0.0
        
        duration = scenario_results["end_time"] - scenario_results["start_time"]
        
        return {
            "scenario_id": scenario_results["scenario_id"],
            "benchmark_duration_sec": round(duration, 4),
            "operations_requested": events_generated,
            "events_generated": events_generated,  # Assuming 1:1 mapped
            "events_captured": events_captured,
            "events_processed": processed,
            "events_dropped": events_dropped,
            "events_per_sec": round(events_captured / duration if duration > 0 else 0, 2),
            "average_event_latency_sec": round(avg_latency, 6),
            "normalization_latency_sec": round(avg_latency, 6), # Coupled via dataclass creation
            "cpu_overhead_percent": round(max(0, peak_cpu - base_cpu), 2),
            "memory_overhead_bytes": peak_mem - base_mem
        }
