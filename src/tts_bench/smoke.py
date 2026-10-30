from __future__ import annotations

import argparse
import wave
from pathlib import Path
from dataclasses import asdict

import numpy as np

from . import adapters as _  # noqa: F401
from .core.registry import get_adapter
from .core.voices import DirectoryVoiceLibrary



def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tts_bench.smoke")
    p.add_argument("engine")
    p.add_argument("--voice", required=True)
    p.add_argument("--text", default="Hola, esta es una prueba de síntesis de voz en español.")
    p.add_argument("--out", default=None)
    p.add_argument("--voices-dir", default="cloned_voices")
    a = p.parse_args(argv)

    adapter = get_adapter(a.engine)
    adapter.load()  # raises with an install/weights hint when unavailable
    try:
        d = adapter.descriptor
        ref = DirectoryVoiceLibrary(a.voices_dir).resolve(a.voice, d.voice_kind)
        res = adapter.synthesize(a.text, ref)
        d = res.descriptor  # reflects the selected voice
        for k, v in asdict(d).items():
            print(f"{k}: {v}")
        print(f"declared granularity: {d.streaming.granularity}")
        print(f"sample_rate: {res.sample_rate}  samples: {res.audio.size}  chunks: {len(res.chunks)}")
        if res.first_audio_ns is not None:
            print(f"time to first audio: {(res.first_audio_ns - res.request_started_ns) / 1e6:.0f} ms")
        else:
            print("time to first audio: not available")
        print(f"total: {(res.finished_ns - res.request_started_ns) / 1e6:.0f} ms")
        if a.out:
            pcm = res.audio
            if pcm.dtype != np.int16:
                pcm = (np.clip(pcm, -1, 1) * 32767).astype(np.int16)
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            with wave.open(a.out, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(res.sample_rate)  # native rate, no resampling
                w.writeframes(pcm.tobytes())
            print(f"wrote {a.out}")
    finally:
        adapter.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
