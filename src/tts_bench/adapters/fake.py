from __future__ import annotations

import time
from typing import Iterator

import numpy as np

from ..core.adapter import BaseAdapter
from ..core.descriptor import EngineDescriptor, InputLimits, StreamingInfo
from ..core.voices import VoiceReference


class FakeAdapter(BaseAdapter):
    """Deterministic engine with exactly configurable timings (FR-010).

    `fail_after_chunks` makes the engine raise mid-synthesis (failure-path tests).
    For granularity "none" the whole audio arrives after first_chunk_delay_s.
    """

    def __init__(
        self,
        granularity: str = "chunk",
        first_chunk_delay_s: float = 0.05,
        chunk_interval_s: float = 0.02,
        audio_seconds: float = 0.4,
        sample_rate: int = 16000,
        n_chunks: int = 4,
        max_chars: int | None = None,
        fail_after_chunks: int | None = None,
        name: str = "fake",
    ) -> None:
        super().__init__()
        self.first_chunk_delay_s = first_chunk_delay_s
        self.chunk_interval_s = chunk_interval_s
        self.audio_seconds = audio_seconds
        self.sample_rate = sample_rate
        self.n_chunks = n_chunks
        self.fail_after_chunks = fail_after_chunks
        self.descriptor = EngineDescriptor(
            name=name,
            engine_version="fake-1",
            model_id="fake",
            license_code="n/a",
            license_model="n/a",
            license_flags=(),
            language="es",
            spanish_variant="none (synthetic tone)",
            voice_kind="fixed_voice",
            supports_cloning=False,
            streaming=StreamingInfo(granularity),  # type: ignore[arg-type]
            input_limits=InputLimits(max_chars),
        )

    def _load(self) -> None:
        pass

    def _iter_engine(self, text: str, voice: VoiceReference) -> Iterator[tuple[np.ndarray, int, int]]:
        total = int(self.audio_seconds * self.sample_rate)
        t = np.arange(total) / self.sample_rate
        audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        time.sleep(self.first_chunk_delay_s)
        if self.descriptor.streaming.granularity == "none":
            yield audio, self.sample_rate, 1
            return
        for i, part in enumerate(np.array_split(audio, self.n_chunks)):
            if i > 0:
                time.sleep(self.chunk_interval_s)
            if self.fail_after_chunks is not None and i >= self.fail_after_chunks:
                raise RuntimeError("fake engine failure")
            yield part, self.sample_rate, 1
