from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

FRAME_S = 0.03
MIN_SPEECH_S = 10.0


def _read(path: Path) -> tuple[np.ndarray, int]:
    try:
        with wave.open(str(path), "rb") as w:
            if w.getsampwidth() != 2:
                raise ValueError("not 16-bit")
            rate, ch = w.getframerate(), w.getnchannels()
            raw = w.readframes(w.getnframes())
    except (wave.Error, EOFError, ValueError) as exc:
        raise ValueError(f"{path}: only 16-bit PCM WAV is supported; convert it to 16-bit PCM WAV ({exc})") from exc
    x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if ch > 1:
        x = x[: x.size // ch * ch].reshape(-1, ch).mean(axis=1)
    return x, rate


def analyze(path: Path) -> dict:
    x, rate = _read(Path(path))
    n = max(1, int(rate * FRAME_S))
    frames = x[: x.size // n * n].reshape(-1, n) if x.size >= n else x.reshape(1, -1)
    rms = np.sqrt((frames**2).mean(axis=1))
    level = 20 * np.log10(np.maximum(rms, 1e-10))
    floor = float(np.percentile(level, 10))
    speech_frames = int((level >= floor + 10).sum())
    return {
        "sample_rate": rate,
        "duration_s": round(x.size / rate, 3),
        "speech_seconds": round(speech_frames * FRAME_S, 3),
        "snr_estimate_db": round(float(np.percentile(level, 90)) - floor, 2),
    }


def warnings(analysis: dict, noise_threshold_db: float = 20.0) -> list[str]:
    out = []
    if analysis["speech_seconds"] < MIN_SPEECH_S:
        out.append("too_short")
    if analysis["snr_estimate_db"] < noise_threshold_db:
        out.append("noisy")
    return out


def write_segment(src: Path, dst: Path, start_s: float, length_s: float) -> None:
    with wave.open(str(src), "rb") as w:
        rate, ch, width, total = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        first = min(max(int(start_s * rate), 0), total)
        last = min(first + int(length_s * rate), total)
        w.setpos(first)
        data = w.readframes(last - first)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as o:
        o.setnchannels(ch)
        o.setsampwidth(width)
        o.setframerate(rate)
        o.writeframes(data)
