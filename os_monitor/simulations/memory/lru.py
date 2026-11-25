"""
Page Replacement - LRU (Least Recently Used)
The page that has not been used for the longest time is replaced.
"""
from typing import List
from .fifo import PageReplacementResult


def lru(reference_string: List[int], num_frames: int) -> PageReplacementResult:
    """
    LRU Page Replacement.
    Tracks the last access time of each page.
    On a fault, evicts the page with the smallest last_used index.
    """
    frames = []
    last_used = {}   # page -> last index it was referenced
    page_faults = 0
    page_hits = 0
    frame_states = []

    for i, page in enumerate(reference_string):
        if page in frames:
            page_hits += 1
            last_used[page] = i
        else:
            page_faults += 1
            if len(frames) < num_frames:
                frames.append(page)
            else:
                # Evict page least recently used
                lru_page = min(frames, key=lambda p: last_used.get(p, -1))
                idx = frames.index(lru_page)
                del last_used[lru_page]
                frames[idx] = page

            last_used[page] = i

        frame_states.append(frames[:])

    total = len(reference_string)
    return PageReplacementResult(
        algorithm="LRU",
        reference_string=reference_string,
        num_frames=num_frames,
        page_faults=page_faults,
        page_hits=page_hits,
        fault_rate=round(page_faults / total, 4),
        hit_rate=round(page_hits / total, 4),
        frame_states=frame_states,
    )
