"""
Page Replacement - Clock (Second Chance) Algorithm
Simulates a circular buffer of page frames with reference bits.
"""
from typing import List
from os_monitor.simulations.memory.fifo import PageReplacementResult


def clock(reference_string: List[int], num_frames: int) -> PageReplacementResult:
    """
    Clock (Second Chance) Page Replacement algorithm.
    Each frame has a reference bit. When replacing, the clock hand advances,
    clearing reference bits until a page with bit 0 is found and replaced.
    """
    if num_frames <= 0 or not reference_string:
        return PageReplacementResult(
            algorithm="CLOCK",
            reference_string=reference_string,
            num_frames=num_frames,
            page_faults=0,
            page_hits=0,
            fault_rate=0.0,
            hit_rate=0.0,
            frame_states=[],
        )

    frames: List[int] = []
    ref_bits: dict[int, int] = {}
    hand = 0
    page_faults = 0
    page_hits = 0
    frame_states: List[List[int]] = []

    for page in reference_string:
        if page in frames:
            page_hits += 1
            ref_bits[page] = 1
        else:
            page_faults += 1
            if len(frames) < num_frames:
                frames.append(page)
                ref_bits[page] = 1
            else:
                # Clock hand searches for page with ref_bit == 0
                while True:
                    victim = frames[hand]
                    if ref_bits.get(victim, 0) == 1:
                        ref_bits[victim] = 0
                        hand = (hand + 1) % num_frames
                    else:
                        # Evict victim and place new page
                        frames[hand] = page
                        ref_bits[page] = 1
                        hand = (hand + 1) % num_frames
                        break

        frame_states.append(list(frames))

    total = len(reference_string)
    return PageReplacementResult(
        algorithm="CLOCK",
        reference_string=reference_string,
        num_frames=num_frames,
        page_faults=page_faults,
        page_hits=page_hits,
        fault_rate=round(page_faults / total, 4) if total > 0 else 0.0,
        hit_rate=round(page_hits / total, 4) if total > 0 else 0.0,
        frame_states=frame_states,
    )

