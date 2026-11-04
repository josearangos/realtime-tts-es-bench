"""RMS loudness normalization with a peak limiter; stdlib WAV I/O (16-bit mono)."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Return float samples in [-1, 1] (mono; multi-channel is averaged) and the sample rate."""
    with wave.open(str(path), "rb") as w:
        n_ch, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
        frames = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError(f"{path}: only 16-bit PCM WAV is supported")
    x = np.frombuffer(frames, dtype="<i2").astype(np.float64) / 32768.0
    if n_ch > 1:
        x = x.reshape(-1, n_ch).mean(axis=1)
    return x, rate


def write_wav(path: str | Path, samples: np.ndarray, rate: int) -> None:
    pcm = np.clip(np.round(np.asarray(samples) * 32768.0), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:  # stdlib writes no metadata chunks
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def rms_dbfs(x: np.ndarray) -> float:
    if x.size == 0:
        return float("-inf")
    r = float(np.sqrt(np.mean(np.square(x))))
    return float("-inf") if r <= 0 else 20 * np.log10(r)


def peak_dbfs(x: np.ndarray) -> float:
    p = float(np.max(np.abs(x))) if x.size else 0.0
    return float("-inf") if p <= 0 else 20 * np.log10(p)


def normalize(x: np.ndarray, rms_target_dbfs: float = -23.0, peak_limit_dbfs: float = -1.0) -> np.ndarray:
    """Scale to the RMS target, then lower the gain if the peak would exceed the limit.

    Silence is returned unchanged. When the limit wins, RMS ends below target (documented limitation).
    """
    x = np.asarray(x, dtype=np.float64)
    cur = rms_dbfs(x)
    if not np.isfinite(cur):
        return x.copy()
    gain_db = rms_target_dbfs - cur
    peak_after = peak_dbfs(x) + gain_db
    if peak_after > peak_limit_dbfs:
        gain_db -= peak_after - peak_limit_dbfs
    return x * (10 ** (gain_db / 20))
