import wave
from pathlib import Path

import numpy as np
import pytest

from tts_bench.voices import ConsentRecord, LocalVoiceLibrary


def make_wav(path: Path, speech_s: float, noise_db: float = -60.0, rate: int = 24000, bits: int = 16) -> Path:
    """Sine bursts (loud) alternating with silence; background noise at `noise_db` dBFS."""
    rng = np.random.default_rng(0)
    n = int(speech_s * 2 * rate)  # half speech, half pause
    t = np.arange(n) / rate
    burst = (np.sin(2 * np.pi * 220 * t) * 0.3) * ((t % 1.0) < 0.5)
    x = burst + rng.normal(0, 10 ** (noise_db / 20), n)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2 if bits == 16 else 1)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes() if bits == 16 else (pcm >> 8).astype("i1").tobytes())
    return path


@pytest.fixture
def wav_factory(tmp_path):
    def f(name="a.wav", speech_s=12, **kw):
        return make_wav(tmp_path / name, speech_s, **kw)

    return f


@pytest.fixture
def library(tmp_path):
    return LocalVoiceLibrary(tmp_path / "lib")


def full_consent(alias="ana", uses=("internal_benchmarking", "published_results", "published_demo_audio", "human_evaluation")):
    return ConsentRecord(alias, "2025", list(uses), ["outbound_sales", "cloning_prompts"])


@pytest.fixture
def consented(library):
    library.add_consent(full_consent())
    return library


@pytest.fixture
def recording(consented, wav_factory):
    return consented.add_recording(wav_factory(), "ana", "es-CO", no_music_confirmed=True)


def register_fake(lib, rec, name="v1", engine="fake", segment=None):
    f = lib.root.parent / f"{name}.bin"
    f.write_bytes(b"voice-" + name.encode())
    lib.register(
        name, engine, "stored_voice_file", f, recording_id=rec.recording_id,
        segment=segment or {"start_s": 0, "length_s": 10}, creation="external: test", accent_label="es-CO",
    )
