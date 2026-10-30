from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .descriptor import EngineDescriptor


@dataclass(frozen=True)
class AudioChunk:
    samples: np.ndarray  # as produced by the engine (float32 or int16); never resampled
    sample_rate: int
    channels: int
    produced_at_ns: int  # time.perf_counter_ns() at receipt
    index: int


@dataclass(frozen=True)
class SynthesisResult:
    audio: np.ndarray
    sample_rate: int
    request_started_ns: int
    first_audio_ns: int | None  # None when granularity is "none"
    finished_ns: int
    chunks: list[AudioChunk]
    descriptor: EngineDescriptor = field(repr=False)
