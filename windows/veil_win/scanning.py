"""Scan pacing and measured whole-display-cycle timing."""
from collections import deque
from dataclasses import dataclass

MIN_IDLE_SECONDS = .005


def scan_delay(interval_ms: int, elapsed_seconds: float) -> float:
    # One scan at a time. Never accumulate missed timer ticks or catch-up work.
    return max(MIN_IDLE_SECONDS, interval_ms/1000 - elapsed_seconds)


def interval_label(interval_ms: int) -> str:
    if interval_ms == 0:
        return "Scan interval: Fastest available"
    return f"Scan interval: {interval_ms} ms · up to {1000/interval_ms:.1f} scans/sec"


@dataclass(frozen=True)
class ScanTiming:
    work_ms: float
    scans_per_second: float | None


class ScanMeter:
    def __init__(self):
        self.work = deque(maxlen=8)
        self.periods = deque(maxlen=8)
        self.previous_start = None

    def observe(self, started: float, finished: float) -> ScanTiming:
        self.work.append(max(0, finished-started)*1000)
        if self.previous_start is not None and started > self.previous_start:
            self.periods.append(started-self.previous_start)
        self.previous_start = started
        rate = len(self.periods)/sum(self.periods) if self.periods else None
        return ScanTiming(sum(self.work)/len(self.work), rate)
