"""Silence and empty detection on a WAV (standard library plus numpy)."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SILENCE_PEAK = 1e-4  # float scale, about -80 dBFS


def to_float(samples: np.ndarray) -> np.ndarray:
    """int16 (and other integer) input is scaled to [-1, 1] before any threshold."""
    arr = np.asarray(samples)
    if np.issubdtype(arr.dtype, np.integer):
        return arr.astype(np.float64) / float(np.iinfo(arr.dtype).max + 1)
    return arr.astype(np.float64)


def is_silent(samples: np.ndarray) -> bool:
    """A signal is silent if it has zero samples or its peak absolute amplitude is below 1e-4."""
    x = to_float(samples)
    return x.size == 0 or float(np.max(np.abs(x))) < SILENCE_PEAK


def inspect_wav(path: str | Path) -> dict:
    """-> {duration_s, sample_rate, peak, silent}; handles mono, stereo, 8/16/32-bit PCM."""
    with wave.open(str(path), "rb") as w:
        rate, width, channels, frames = w.getframerate(), w.getsampwidth(), w.getnchannels(), w.getnframes()
        raw = w.readframes(frames)
    if width == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    elif width == 2:
        x = to_float(np.frombuffer(raw, dtype="<i2"))
    elif width == 4:
        x = to_float(np.frombuffer(raw, dtype="<i4"))
    else:
        raise ValueError(f"unsupported sample width {width} bytes")
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    return {
        "duration_s": (frames / rate) if rate else 0.0,
        "sample_rate": rate,
        "peak": peak,
        "silent": x.size == 0 or peak < SILENCE_PEAK,
    }
