"""PCM16 conversion and WAV packaging. The sample rate is never changed."""

from __future__ import annotations

import io
import wave

import numpy as np


def float_to_pcm16(samples) -> bytes:
    arr = np.asarray(samples)
    if arr.dtype == np.int16:
        return arr.astype("<i2").tobytes()
    clipped = np.clip(arr.astype(np.float32), -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


def pcm16_to_wav(pcm: bytes, sample_rate: int, channels: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()
