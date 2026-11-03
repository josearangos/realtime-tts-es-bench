"""Shared fixtures for the speaker tests: fixed vectors, fakes and synthetic WAV files.

No model weights, no network and no English text (sentences come from the Spanish corpus).
"""

import wave
from dataclasses import dataclass

import numpy as np
import pytest

from tts_bench.adapters.fake import FakeAdapter
from tts_bench.core.voices import VoiceReference
from tts_bench.corpus import Corpus, load_corpus
from tts_bench.speaker.embedder import FakeEmbedder
from tts_bench.speaker.model import (
    ClipEmbedding, EmbeddingsFile, ExtraEmbedding, ReferenceQuality,
)
from tts_bench.voices import ConsentRecord, LocalVoiceLibrary


def write_wav(path, samples, rate=16000):
    """Write float samples in [-1, 1] (mono) as PCM16."""
    x = np.asarray(samples, dtype=np.float64)
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return path


def tone_audio(seconds=0.3, rate=16000, hz=440.0, amp=0.1):
    t = np.arange(int(seconds * rate)) / rate
    return amp * np.sin(2 * np.pi * hz * t)


def silent_audio(seconds=0.3, rate=16000):
    return np.zeros(int(seconds * rate))


REFERENCE = ReferenceQuality("rec-test", 16.3, 14.0, 48.2, "es-CO", ())
ENGINE = {"name": "fake", "engine_version": "fake-1", "model_id": "fake", "spanish_variant": "none",
          "supports_cloning": True, "voice": {"name": "voz-a", "kind": "reference_audio"}}
CORPUS = {"corpus_version": "t", "corpus_hash": "h", "subset": "cloning", "limit": None}


def fixed_embeddings(mapping, *, reference=(1.0, 0.0, 0.0), repetitions=1, engine=None, durations=None,
                     statuses=None, extras=(), reference_quality=None, corpus=None, embedder=None,
                     reference_sha="ref-sha"):
    """EmbeddingsFile from {(sentence_id, repetition) or sentence_id: vector}.

    `durations` and `statuses` are optional {key: value} overrides; the default duration is 4.0 s.
    A vector of None gives a clip without a vector.
    """
    durations, statuses = durations or {}, statuses or {}
    clips = []
    for key, vec in mapping.items():
        sid, rep = key if isinstance(key, tuple) else (key, 1)
        status = statuses.get(key, "ok" if vec is not None else "failed")
        clips.append(ClipEmbedding(
            sid, rep, f"sha-{sid}-{rep}" if status != "failed" else None, durations.get(key, 4.0),
            None if vec is None else tuple(float(v) for v in vec), status))
    return EmbeddingsFile(
        embedder or FakeEmbedder().record(), engine or ENGINE, corpus or CORPUS, repetitions, 1,
        reference_quality or REFERENCE, reference_sha, tuple(float(v) for v in reference), tuple(clips),
        tuple(ExtraEmbedding(label, "other_voice_reference", f"x-{label}", tuple(v)) for label, v in extras),
        "python -m tts_bench.speaker test", {})


@pytest.fixture
def cloning_corpus():
    return load_corpus(subset="cloning")


@pytest.fixture
def mini_corpus():
    def _mini(n: int) -> Corpus:
        full = load_corpus(subset="cloning")
        return Corpus(full.version, full.content_hash, full.sentences[:n])

    return _mini


@pytest.fixture
def make_adapter():
    created = []

    def _make(**kw):
        kw.setdefault("supports_cloning", True)
        a = FakeAdapter(first_chunk_delay_s=0, chunk_interval_s=0, **kw)
        created.append(a)
        return a

    yield _make
    for a in created:
        a.close()


@pytest.fixture
def voice_ref():
    return VoiceReference("voz-a", "reference_audio", "memory://voz-a")


@dataclass
class FakeLibrary:
    lib: LocalVoiceLibrary
    recording_id: str
    reference_voice: str  # kind reference_audio
    stored_voice: str  # kind stored_voice_file


@pytest.fixture
def fake_voice_library(tmp_path):
    """A consented library with a synthetic recording and two cloned voices (no real voices)."""
    lib = LocalVoiceLibrary(tmp_path / "lib")
    lib.add_consent(ConsentRecord("ana", "2025", ["internal_benchmarking"], ["cloning_prompts"]))
    # tone bursts alternating with near-silence, so the library measures speech seconds and SNR
    t = np.arange(int(24.0 * 24000)) / 24000
    burst = 0.3 * np.sin(2 * np.pi * 220 * t) * ((t % 1.0) < 0.5)
    noise = np.random.default_rng(0).normal(0, 0.001, t.size)
    src = write_wav(tmp_path / "rec.wav", burst + noise, 24000)
    rec = lib.add_recording(src, "ana", "es-CO", no_music_confirmed=True)
    seg = lib.prepare_segment(rec.recording_id, "fake", 0.0, 20.0, dest=tmp_path / "ref.wav")
    lib.register("voz-ref", "fake", "reference_audio", seg, recording_id=rec.recording_id,
                 segment={"start_s": 0.0, "length_s": 20.0}, creation="automated", accent_label="es-CO")
    blob = tmp_path / "voz.bin"
    blob.write_bytes(b"voice-blob")
    lib.register("voz-stored", "fake", "stored_voice_file", blob, recording_id=rec.recording_id,
                 segment={"start_s": 0.0, "length_s": 20.0}, creation="external: test", accent_label="es-CO")
    return FakeLibrary(lib, rec.recording_id, "voz-ref", "voz-stored")
