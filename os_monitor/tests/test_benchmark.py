import os
import unittest
from os_monitor.core.stream import LiveEventStream
from os_monitor.adapters.windows_adapter import WindowsAdapter
from os_monitor.benchmark.engine import OSBenchmarkEngine
from os_monitor.benchmark.scenarios import (
    FileCreateScenario, 
    FileOpenReadWriteScenario, 
    FileRenameDeleteScenario, 
    DirectoryOperationsScenario, 
    ProcessOperationsScenario,
    ResourceStressScenario,
    MixedOSWorkloadScenario
)

class TestOSMonitorBenchmark(unittest.TestCase):
    def setUp(self):
        self.stream = LiveEventStream(max_size=1000)
        self.adapter = WindowsAdapter(self.stream, watch_paths=["."])
        self.engine = OSBenchmarkEngine(self.stream, self.adapter)

    def test_all_scenarios(self):
        scenarios = [
            FileCreateScenario("FILE_CREATE_10", 10),
            FileOpenReadWriteScenario("FILE_RW_10", 10),
            FileRenameDeleteScenario("FILE_RN_RM_10", 10),
            DirectoryOperationsScenario("DIR_OPS_5", 5),
            ProcessOperationsScenario("PROC_OPS_2", 2),
            ResourceStressScenario("RES_STRESS_1", 1),
            MixedOSWorkloadScenario("MIXED_2", 2)
        ]
        
        for sc in scenarios:
            results = self.engine.run_scenario(sc)
            self.assertEqual(results["scenario_id"], sc.scenario_id)
            self.assertTrue(results["operations_requested"] > 0)
            self.assertTrue(results["events_processed"] >= 0)
            self.assertTrue("average_event_latency_sec" in results)
            
            print(f"\n--- Benchmark Results: {sc.scenario_id} ---")
            for k, v in results.items():
                print(f"{k}: {v}")

if __name__ == "__main__":
    unittest.main()
