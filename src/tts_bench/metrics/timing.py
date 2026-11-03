"""Shared pure timing arithmetic (standard library only).

Used by the offline harness (`metrics/runner.py`) and by the real-time backend worker so
both compute TTFA, generation time and RTF with the same definitions (docs/metrics.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import ChunkTiming

NS_PER_MS = 1e6


@dataclass(frozen=True)
class TimingResult:
    generation_ms: float
    ttfa_ms: float | None
    rtf: float | None
    chunks: tuple[ChunkTiming, ...]


def timing_from_marks(
    request_started_ns: int,
    chunks: list[tuple[int, int, int]],
    finished_ns: int,
    audio_seconds: float,
    streams: bool,
) -> TimingResult:
    """`chunks` is a list of `(index, produced_at_ns, n_samples)`.

    TTFA is the first chunk with samples, relative to the request start; None when the
    engine does not stream. RTF is never computed for non-positive audio duration.
    """
    generation_ms = (finished_ns - request_started_ns) / NS_PER_MS
    timings: list[ChunkTiming] = []
    prev = request_started_ns
    ttfa_ms = None
    for index, produced_ns, n_samples in chunks:
        at = (produced_ns - request_started_ns) / NS_PER_MS
        timings.append(ChunkTiming(index, at, (produced_ns - prev) / NS_PER_MS))
        prev = produced_ns
        if streams and ttfa_ms is None and n_samples > 0:
            ttfa_ms = at
    rtf = generation_ms / 1000.0 / audio_seconds if audio_seconds > 0 else None
    return TimingResult(generation_ms, ttfa_ms, rtf, tuple(timings))
