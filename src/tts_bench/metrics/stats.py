"""Pure statistics over measurement lists. No engine, no I/O (FR-010)."""

from __future__ import annotations

import statistics
from typing import Iterable, Sequence

import numpy as np

from .model import Measurement, RunSummary

LOW_SAMPLE = 20
UNRELIABLE_FRACTION = 0.10
NOT_AVAILABLE = "not available"


def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile (NumPy default); q in 0..100."""
    if not values:
        raise ValueError("percentile of an empty list")
    return float(np.percentile(np.asarray(values, dtype=float), q))


def _dist(values: Sequence[float]) -> dict:
    if not values:
        return {"p50": None, "p95": None, "mean": None, "n": 0, "p95_low_sample": True}
    return {
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "mean": float(statistics.fmean(values)),
        "n": len(values),
        "p95_low_sample": len(values) < LOW_SAMPLE,
    }


def _values(ms: Iterable[Measurement], attr: str) -> list[float]:
    return [getattr(m, attr) for m in ms if getattr(m, attr) is not None]


def summarize(
    measurements: Iterable[Measurement],
    *,
    windows_s: dict[int, float] | None = None,
    load_time_ms: float | None = None,
    warmup: dict | None = None,
) -> RunSummary:
    """Summarize steady-state measurements.

    `windows_s` maps repetition -> wall seconds from the first measured request start to
    the last measured request finish; it is needed for throughput. Only `ok` + `steady`
    measurements enter distributions; the `first_request` one is reported apart.
    """
    ms = list(measurements)
    steady = [m for m in ms if m.phase == "steady"]
    ok = [m for m in steady if m.status == "ok"]
    n_failed = sum(m.status == "failed" for m in steady)
    n_invalid = sum(m.status == "invalid" for m in steady)
    n_total = len(steady)

    out: dict = {
        "n_ok": len(ok),
        "n_failed": n_failed,
        "n_invalid": n_invalid,
        "n_total": n_total,
        "reliable": (n_failed + n_invalid) <= UNRELIABLE_FRACTION * n_total,
        "rtf": _dist(_values(ok, "rtf")),
        "generation_ms": _dist(_values(ok, "generation_ms")),
    }
    ttfa = _values(ok, "ttfa_ms")
    if ttfa:
        out["ttfa_ms"] = _dist(ttfa)
    else:
        out["ttfa_ms"] = NOT_AVAILABLE
        out["ttfa_note"] = "engine does not stream audio (granularity none) or no request succeeded"

    per_rep: list[float] = []
    if windows_s:
        for rep in sorted(windows_s):
            audio = sum(m.audio_seconds for m in ok if m.repetition == rep)
            if windows_s[rep] > 0 and audio > 0:
                per_rep.append(audio / windows_s[rep])
    if per_rep:
        out["throughput_audio_s_per_s"] = {"median": float(statistics.median(per_rep)), "per_repetition": per_rep}
    else:
        out["throughput_audio_s_per_s"] = NOT_AVAILABLE

    if load_time_ms is not None:
        out["load_time_ms"] = load_time_ms
    first = next((m for m in ms if m.phase == "first_request"), None)
    if first is not None:
        p50 = out["generation_ms"]["p50"]
        penalty = None
        if first.generation_ms is not None and p50 is not None:
            penalty = first.generation_ms - p50
        out["first_request"] = {
            "sentence_id": first.sentence_id,
            "status": first.status,
            "generation_ms": first.generation_ms,
            "ttfa_ms": first.ttfa_ms,
            "rtf": first.rtf,
            "penalty_ms": penalty,
        }
    if warmup is not None:
        out["warmup"] = warmup
    return RunSummary(out)
