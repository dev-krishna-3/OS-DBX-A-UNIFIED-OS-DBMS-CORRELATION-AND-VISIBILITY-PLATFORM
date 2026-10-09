"""
Page Replacement - FIFO (First In First Out)
Oldest page in memory is replaced first when a page fault occurs.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class PageReplacementResult:
    algorithm: str
    reference_string: List[int]
    num_frames: int
    page_faults: int
    page_hits: int
    fault_rate: float
    hit_rate: float
    frame_states: List[List[int]]   # Snapshot of frames after each reference


def fifo(reference_string: List[int], num_frames: int) -> PageReplacementResult:
    """
    FIFO Page Replacement.
    Maintains a queue; when full, the oldest (front of queue) is evicted.
    """
    frames = []
    order = []          # Tracks insertion order for FIFO eviction
    page_faults = 0
    page_hits = 0
    frame_states = []

    for page in reference_string:
        if page in frames:
            page_hits += 1
        else:
            page_faults += 1
            if len(frames) < num_frames:
                frames.append(page)
                order.append(page)
            else:
                # Evict the oldest page
                oldest = order.pop(0)
                idx = frames.index(oldest)
                frames[idx] = page
                order.append(page)

        frame_states.append(frames[:])

    total = len(reference_string)
    return PageReplacementResult(
        algorithm="FIFO",
        reference_string=reference_string,
        num_frames=num_frames,
        page_faults=page_faults,
        page_hits=page_hits,
        fault_rate=round(page_faults / total, 4),
        hit_rate=round(page_hits / total, 4),
        frame_states=frame_states,
    )
