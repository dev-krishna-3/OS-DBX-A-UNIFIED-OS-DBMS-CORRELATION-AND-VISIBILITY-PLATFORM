"""
Page Replacement - Optimal (OPT / Belady's Algorithm)
Replaces the page that will NOT be used for the longest time in the future.
This is the theoretically best algorithm — used as a benchmark comparison.
"""
from typing import List
from .fifo import PageReplacementResult


def optimal(reference_string: List[int], num_frames: int) -> PageReplacementResult:
    """
    Optimal Page Replacement (Belady's Algorithm).
    Requires future knowledge of the reference string.
    """
    frames = []
    page_faults = 0
    page_hits = 0
    frame_states = []
    n = len(reference_string)

    for i, page in enumerate(reference_string):
        if page in frames:
            page_hits += 1
        else:
            page_faults += 1
            if len(frames) < num_frames:
                frames.append(page)
            else:
                # For each page in frames, find its NEXT use after position i
                def next_use(p):
                    for j in range(i + 1, n):
                        if reference_string[j] == p:
                            return j
                    return float('inf')  # Never used again -> ideal victim

                victim = max(frames, key=next_use)
                frames[frames.index(victim)] = page

        frame_states.append(frames[:])

    total = n
    return PageReplacementResult(
        algorithm="Optimal (OPT)",
        reference_string=reference_string,
        num_frames=num_frames,
        page_faults=page_faults,
        page_hits=page_hits,
        fault_rate=round(page_faults / total, 4),
        hit_rate=round(page_hits / total, 4),
        frame_states=frame_states,
    )
