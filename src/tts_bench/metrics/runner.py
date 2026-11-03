"""Cold/warm measurement protocol around an engine adapter.

Metric start and end instants are documented in docs/metrics.md. The harness reads
monotonic clocks only; it never writes audio or collects garbage inside a timed request.
"""

from __future__ import annotations

import gc
import os
import time
from dataclasses import dataclass, field

from ..core.errors import EmptyAudioError, TTSBenchError
from ..core.voices import VoiceReference
from .model import Measurement
from .timing import timing_from_marks

NS_PER_MS = 1e6


def _audio_seconds(result) -> float:
    audio = result.audio
    channels = result.chunks[0].channels if result.chunks else 1
    if audio.ndim > 1:
        frames = audio.shape[0]
    else:
        frames = audio.size // max(channels, 1)
    return frames / result.sample_rate if result.sample_rate else 0.0


def _timed_call(adapter, sentence, voice, repetition: int, phase: str) -> tuple[Measurement, int, int]:
    t0 = time.perf_counter_ns()
    try:
        result = adapter.synthesize(sentence.text, voice)
    except EmptyAudioError as exc:
        t1 = time.perf_counter_ns()
        return Measurement(sentence.id, repetition, phase, "invalid", error=str(exc)), t0, t1
    except TTSBenchError as exc:
        t1 = time.perf_counter_ns()
        return Measurement(sentence.id, repetition, phase, "failed", error=str(exc)), t0, t1
    t1 = time.perf_counter_ns()

    seconds = _audio_seconds(result)
    if result.audio.size == 0 or seconds <= 0:
        return Measurement(sentence.id, repetition, phase, "invalid", error="zero-length audio"), t0, t1

    streams = result.descriptor.streaming.granularity != "none"
    marks = [(c.index, c.produced_at_ns, int(c.samples.size)) for c in result.chunks]
    timing = timing_from_marks(result.request_started_ns, marks, result.finished_ns, seconds, streams)
    m = Measurement(
        sentence.id, repetition, phase, "ok",
        audio_seconds=seconds, generation_ms=timing.generation_ms, rtf=timing.rtf,
        ttfa_ms=timing.ttfa_ms, chunks=timing.chunks,
    )
    return m, t0, t1


def measure_request(adapter, sentence, voice: VoiceReference, repetition: int, phase: str) -> Measurement:
    """One synthesis request turned into a Measurement. Never raises for engine failures."""
    return _timed_call(adapter, sentence, voice, repetition, phase)[0]


def run_repetitions(
    adapter, corpus, voice: VoiceReference, repetitions: int, *, first_rep_skip: int = 0
) -> tuple[list[Measurement], dict[int, float]]:
    """Run the corpus `repetitions` times in corpus order; return measurements and the
    wall-clock window (seconds) of each repetition for throughput.

    `first_rep_skip` skips that many leading sentences of repetition 1 (they were measured
    elsewhere as the cold first request)."""
    measurements: list[Measurement] = []
    windows: dict[int, float] = {}
    for rep in range(1, repetitions + 1):
        gc.collect()  # once per repetition, never between requests
        sentences = corpus.sentences[first_rep_skip:] if rep == 1 else corpus.sentences
        first_start = last_end = None
        for s in sentences:
            m, t0, t1 = _timed_call(adapter, s, voice, rep, "steady")
            measurements.append(m)
            if first_start is None:
                first_start = t0
            last_end = t1
        if first_start is not None:
            windows[rep] = (last_end - first_start) / 1e9
    return measurements, windows


@dataclass
class ProtocolResult:
    measurements: list[Measurement]
    windows_s: dict[int, float]
    load_time_ms: float
    warmup: dict | None = None
    phases: dict = field(default_factory=dict)  # wall-clock marks for resource accounting


def run_protocol(
    adapter, corpus, voice: VoiceReference, *, mode: str, repetitions: int = 5, warmup: int = 3
) -> ProtocolResult:
    """load -> (first request | warm-up) -> repetitions. `adapter.close()` is the caller's job."""
    if mode not in ("cold", "warm"):
        raise ValueError(f"mode must be 'cold' or 'warm', got {mode!r}")
    t0 = time.perf_counter_ns()
    adapter.load()
    load_ms = (time.perf_counter_ns() - t0) / NS_PER_MS
    from . import resources

    ram_after_load = resources.peak_ram_mib()[0]

    first: list[Measurement] = []
    warm_info = None
    skip = 0
    if mode == "cold":
        if corpus.sentences:
            first.append(measure_request(adapter, corpus.sentences[0], voice, 1, "first_request"))
            skip = 1
    else:
        failed = 0
        for i in range(warmup):
            s = corpus.sentences[i % len(corpus.sentences)]
            if measure_request(adapter, s, voice, 0, "warmup").status != "ok":
                failed += 1
        warm_info = {"requests": warmup, "discarded": True, "failed": failed}
    steady, windows = run_repetitions(adapter, corpus, voice, repetitions, first_rep_skip=skip)
    return ProtocolResult(first + steady, windows, load_ms, warm_info, {"ram_after_load": ram_after_load})


def run_benchmark(
    adapter, corpus, voice: VoiceReference, *, mode: str, repetitions: int = 5, warmup: int = 3,
    voice_info: dict | None = None, config: dict | None = None, argv: list[str] | None = None,
    load_threshold: float = 0.25,
):
    """Run the whole protocol and return a ResultsFile. Always closes the adapter."""
    from . import resources
    from .environment import collect_environment
    from .model import ResultsFile
    from .stats import summarize

    cfg = {"mode": mode, "repetitions": repetitions, "warmup": warmup if mode == "warm" else None,
           "subset": "main", "limit": None, "load_threshold": load_threshold, **(config or {})}
    info = voice_info or {"name": voice.name, "kind": voice.kind, "checksum": None}
    load_before = resources.load_per_core()
    try:
        timer = resources.CpuTimer()
        with timer:
            proto = run_protocol(adapter, corpus, voice, mode=mode, repetitions=repetitions, warmup=warmup)
        ram_final, ram_method = resources.peak_ram_mib()
        vram, vram_note = resources.peak_vram_mib()
    finally:
        adapter.close()
    load_after = resources.load_per_core()
    res = {
        "peak_ram_mib_after_load": proto.phases["ram_after_load"],
        "peak_ram_mib_final": ram_final,
        "ram_method": ram_method,
        "cpu_percent_of_one_core": timer.percent_of_one_core,
        "logical_cores": os.cpu_count(),
        "peak_vram_mib": vram,
        "background_load": resources.background_load(load_threshold, load_before, load_after),
    }
    if vram_note:
        res["vram_note"] = vram_note
    env = collect_environment(adapter, info, corpus, cfg, argv or [])
    summary = summarize(
        proto.measurements, windows_s=proto.windows_s, load_time_ms=proto.load_time_ms, warmup=proto.warmup
    )
    return ResultsFile(env, summary, res, tuple(proto.measurements))
