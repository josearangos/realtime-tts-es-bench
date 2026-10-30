from __future__ import annotations

import time
from typing import Iterator, Protocol

import numpy as np

from .audio import AudioChunk, SynthesisResult
from .descriptor import EngineDescriptor
from .errors import (
    EngineAlreadyLoadedError,
    InputLimitError,
    StreamingNotSupportedError,
    SynthesisError,
    TTSBenchError,
)
from .voices import VoiceReference

_LOADED: str | None = None  # one engine per process (FR-013)


class EngineAdapter(Protocol):
    descriptor: EngineDescriptor

    def load(self) -> float: ...
    def synthesize(self, text: str, voice: VoiceReference) -> SynthesisResult: ...
    def stream(self, text: str, voice: VoiceReference) -> Iterator[AudioChunk]: ...
    def close(self) -> None: ...


class BaseAdapter:
    """Guard, input limits, timing and error wrapping. Subclasses implement
    `_load()` and `_iter_engine(text, voice)` yielding (samples, sample_rate, channels)."""

    descriptor: EngineDescriptor

    def __init__(self) -> None:
        self._loaded = False

    # -- lifecycle -------------------------------------------------------
    def load(self) -> float:
        global _LOADED
        if _LOADED is not None:
            raise EngineAlreadyLoadedError(
                f"Engine '{_LOADED}' is already loaded in this process; "
                f"close() it before loading '{self.descriptor.name}'."
            )
        start = time.perf_counter()
        self._load()  # may raise EngineNotInstalledError / WeightsMissingError
        _LOADED = self.descriptor.name
        self._loaded = True
        return time.perf_counter() - start

    def close(self) -> None:
        global _LOADED
        if self._loaded:
            self._close()
            self._loaded = False
            if _LOADED == self.descriptor.name:
                _LOADED = None

    # -- hooks -----------------------------------------------------------
    def _load(self) -> None:
        raise NotImplementedError

    def _close(self) -> None:
        pass

    def _iter_engine(self, text: str, voice: VoiceReference) -> Iterator[tuple[np.ndarray, int, int]]:
        raise NotImplementedError

    # -- public API ------------------------------------------------------
    def _check(self, text: str) -> None:
        if not self._loaded:
            raise SynthesisError(f"Engine '{self.descriptor.name}' is not loaded; call load() first.")
        limit = self.descriptor.input_limits.max_chars
        if limit is not None and len(text) > limit:
            raise InputLimitError(
                f"Text has {len(text)} chars; '{self.descriptor.name}' accepts at most {limit}."
            )

    def stream(self, text: str, voice: VoiceReference) -> Iterator[AudioChunk]:
        if self.descriptor.streaming.granularity == "none":
            raise StreamingNotSupportedError(
                f"Engine '{self.descriptor.name}' does not stream audio incrementally."
            )
        self._check(text)
        return self._chunks(text, voice)

    def _chunks(self, text: str, voice: VoiceReference) -> Iterator[AudioChunk]:
        seen: list[AudioChunk] = []
        try:
            for i, (samples, rate, channels) in enumerate(self._iter_engine(text, voice)):
                chunk = AudioChunk(samples, rate, channels, time.perf_counter_ns(), i)
                seen.append(chunk)
                yield chunk
        except TTSBenchError:
            raise
        except Exception as exc:
            raise SynthesisError(f"Synthesis failed in '{self.descriptor.name}': {exc}", seen) from exc

    def synthesize(self, text: str, voice: VoiceReference) -> SynthesisResult:
        self._check(text)
        streams = self.descriptor.streaming.granularity != "none"
        chunks: list[AudioChunk] = []
        parts: list[np.ndarray] = []
        rate = 0
        started = time.perf_counter_ns()
        try:
            for i, (samples, r, channels) in enumerate(self._iter_engine(text, voice)):
                chunk = AudioChunk(samples, r, channels, time.perf_counter_ns(), i)
                chunks.append(chunk)
                parts.append(samples)
                rate = r
        except TTSBenchError:
            raise
        except Exception as exc:
            raise SynthesisError(f"Synthesis failed in '{self.descriptor.name}': {exc}", chunks) from exc
        finished = time.perf_counter_ns()
        if not parts:
            raise SynthesisError(f"Engine '{self.descriptor.name}' produced no audio.")
        return SynthesisResult(
            audio=np.concatenate(parts),
            sample_rate=rate,
            request_started_ns=started,
            first_audio_ns=chunks[0].produced_at_ns if streams else None,
            finished_ns=finished,
            chunks=chunks if streams else [],
            descriptor=self.descriptor,
        )
