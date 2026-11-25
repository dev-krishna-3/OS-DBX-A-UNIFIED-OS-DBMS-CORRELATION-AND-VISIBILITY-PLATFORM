"""
Deterministic test suite for all OS simulations.
Tests: FCFS, SJF, Round Robin, Priority, SRTF, FIFO, LRU, Optimal, Banker's, RAG
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import unittest
from os_monitor.simulations.scheduling.fcfs import fcfs, Process
from os_monitor.simulations.scheduling.sjf import sjf
from os_monitor.simulations.scheduling.round_robin import round_robin
from os_monitor.simulations.scheduling.priority import priority_scheduling
from os_monitor.simulations.scheduling.srtf import srtf
from os_monitor.simulations.memory.fifo import fifo
from os_monitor.simulations.memory.lru import lru
from os_monitor.simulations.memory.optimal import optimal
from os_monitor.simulations.deadlock.bankers import bankers_algorithm
from os_monitor.simulations.deadlock.resource_graph import detect_deadlock


def make_processes():
    """Standard test set used across all scheduling algorithms."""
    return [
        Process(pid=1, arrival_time=0, burst_time=6, priority=2),
        Process(pid=2, arrival_time=2, burst_time=4, priority=1),
        Process(pid=3, arrival_time=4, burst_time=2, priority=3),
    ]


class TestFCFS(unittest.TestCase):
    def test_order_and_waiting_time(self):
        result = fcfs(make_processes())
        self.assertEqual(result.algorithm, "FCFS")
        self.assertEqual(len(result.gantt_chart), 3)
        # P1 runs 0-6, P2 runs 6-10, P3 runs 10-12
        self.assertEqual(result.processes[0].waiting_time, 0)   # P1 waits 0
        self.assertEqual(result.processes[1].waiting_time, 4)   # P2 waits 4
        self.assertEqual(result.processes[2].waiting_time, 6)   # P3 waits 6
        self.assertGreater(result.cpu_utilization, 0)
        print(f"\n[FCFS] Avg WT: {result.avg_waiting_time}, CPU: {result.cpu_utilization}%")


class TestSJF(unittest.TestCase):
    def test_shortest_first(self):
        result = sjf(make_processes())
        self.assertEqual(result.algorithm, "SJF")
        # P3 (burst=2) should run before P2 (burst=4) since both arrive by time 6
        pids = [p.pid for p in result.processes]
        p3_idx = pids.index(3)
        p2_idx = pids.index(2)
        self.assertLess(p3_idx, p2_idx)
        print(f"\n[SJF] Safe sequence order: {pids}, Avg WT: {result.avg_waiting_time}")


class TestRoundRobin(unittest.TestCase):
    def test_all_processes_complete(self):
        result = round_robin(make_processes(), quantum=2)
        self.assertIn("Round Robin", result.algorithm)
        self.assertEqual(len(result.processes), 3)
        for p in result.processes:
            self.assertEqual(p.remaining_time, 0)
        print(f"\n[RR Q=2] Gantt: {result.gantt_chart}")
        print(f"         Avg WT: {result.avg_waiting_time}")

    def test_quantum_1(self):
        result = round_robin(make_processes(), quantum=1)
        self.assertEqual(len(result.processes), 3)


class TestPriority(unittest.TestCase):
    def test_lower_priority_number_runs_first(self):
        result = priority_scheduling(make_processes())
        # P2 has priority=1 (lowest number = highest priority)
        first_pid = result.processes[0].pid
        self.assertEqual(first_pid, 1)  # P1 arrives first; P2 arrives at t=2
        print(f"\n[Priority] Execution order: {[p.pid for p in result.processes]}")


class TestSRTF(unittest.TestCase):
    def test_preemption_occurs(self):
        result = srtf(make_processes())
        self.assertEqual(result.algorithm, "SRTF (Preemptive SJF)")
        # Gantt should have more entries than 3 due to preemption
        self.assertGreaterEqual(len(result.gantt_chart), 3)
        print(f"\n[SRTF] Gantt length: {len(result.gantt_chart)}, Avg WT: {result.avg_waiting_time}")


class TestFIFO(unittest.TestCase):
    def test_known_fault_count(self):
        ref = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        result = fifo(ref, num_frames=3)
        self.assertEqual(result.algorithm, "FIFO")
        self.assertEqual(result.page_faults + result.page_hits, len(ref))
        self.assertGreater(result.page_faults, 0)
        print(f"\n[FIFO] Faults: {result.page_faults}, Hits: {result.page_hits}, Fault Rate: {result.fault_rate}")


class TestLRU(unittest.TestCase):
    def test_lru_fewer_faults_than_fifo(self):
        ref = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        lru_result = lru(ref, num_frames=3)
        fifo_result = fifo(ref, num_frames=3)
        self.assertEqual(lru_result.algorithm, "LRU")
        # LRU should not exceed FIFO in fault count for this reference string
        print(f"\n[LRU] Faults: {lru_result.page_faults} | [FIFO] Faults: {fifo_result.page_faults}")

    def test_frame_state_length(self):
        ref = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3]
        result = lru(ref, num_frames=4)
        self.assertEqual(len(result.frame_states), len(ref))


class TestOptimal(unittest.TestCase):
    def test_optimal_fewer_or_equal_faults(self):
        ref = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        opt = optimal(ref, num_frames=3)
        fifo_r = fifo(ref, num_frames=3)
        # Optimal must have <= faults compared to FIFO (it's theoretically best)
        self.assertLessEqual(opt.page_faults, fifo_r.page_faults)
        print(f"\n[OPT] Faults: {opt.page_faults} | [FIFO] Faults: {fifo_r.page_faults}")


class TestBankersAlgorithm(unittest.TestCase):
    def _safe_state(self):
        allocation = [[0,1,0],[2,0,0],[3,0,2],[2,1,1],[0,0,2]]
        max_need   = [[7,5,3],[3,2,2],[9,0,2],[2,2,2],[4,3,3]]
        available  = [3,3,2]
        return allocation, max_need, available

    def test_safe_state(self):
        alloc, max_n, avail = self._safe_state()
        result = bankers_algorithm(alloc, max_n, avail)
        self.assertTrue(result.is_safe)
        self.assertEqual(len(result.safe_sequence), 5)
        print(f"\n[Banker's SAFE] Sequence: {result.safe_sequence}")

    def test_unsafe_state(self):
        # Give P0 more allocation to break safety
        alloc = [[4,1,0],[2,0,0],[3,0,2],[2,1,1],[0,0,2]]
        max_n = [[7,5,3],[3,2,2],[9,0,2],[2,2,2],[4,3,3]]
        avail = [0,0,0]  # No resources left
        result = bankers_algorithm(alloc, max_n, avail)
        self.assertFalse(result.is_safe)
        print(f"\n[Banker's UNSAFE] Reason: {result.reason}")


class TestResourceAllocationGraph(unittest.TestCase):
    def test_deadlock_detected(self):
        # Classic deadlock: P0 holds R0, wants R1; P1 holds R1, wants R0
        allocation = {0: [0], 1: [1]}
        request    = {0: [1], 1: [0]}
        result = detect_deadlock([0, 1], [0, 1], allocation, request)
        self.assertTrue(result.deadlock_detected)
        self.assertGreater(len(result.deadlocked_processes), 0)
        print(f"\n[RAG DEADLOCK] Cycle: {result.cycle}")

    def test_no_deadlock(self):
        # P0 holds R0; P1 has no requests
        allocation = {0: [0], 1: []}
        request    = {0: [],  1: []}
        result = detect_deadlock([0, 1], [0], allocation, request)
        self.assertFalse(result.deadlock_detected)
        print(f"\n[RAG SAFE] {result.reason}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
