import wave

import numpy as np
import pytest

from tts_bench.adapters.fake import FakeAdapter
from tts_bench.core.voices import VoiceReference
from tts_bench.corpus import Corpus, load_corpus
from tts_bench.intelligibility.model import Transcript, Transcripts
from tts_bench.intelligibility.recognizer import FakeRecognizer


@pytest.fixture
def corpus():
    return load_corpus()


@pytest.fixture
def make_adapter():
    created = []

    def _make(**kw):
        a = FakeAdapter(first_chunk_delay_s=0, chunk_interval_s=0, **kw)
        created.append(a)
        return a

    yield _make
    for a in created:
        a.close()


@pytest.fixture
def voice():
    return VoiceReference("default", "fixed_voice", "memory://default")


@pytest.fixture
def mini_corpus():
    def _mini(n: int) -> Corpus:
        full = load_corpus()
        return Corpus(full.version, full.content_hash, full.sentences[:n])

    return _mini


def write_wav(path, samples, rate=16000):
    """Write float samples in [-1, 1] (mono or (n, ch)) as PCM16."""
    x = np.asarray(samples, dtype=np.float64)
    channels = 1 if x.ndim == 1 else x.shape[1]
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return path


def tone_audio(seconds=0.3, rate=16000, amp=0.1):
    t = np.arange(int(seconds * rate)) / rate
    return amp * np.sin(2 * np.pi * 440 * t)


def silent_audio(seconds=0.3, rate=16000):
    return np.zeros(int(seconds * rate))


def fixed_transcripts(mapping, *, corpus_dict=None, engine=None, statuses=None):
    """Transcripts for {sentence_id: text}; `statuses` overrides the status per id."""
    rec = FakeRecognizer().record()
    statuses = statuses or {}
    items = tuple(
        Transcript(i, f"sha-{i}", statuses.get(i, "ok"), "" if statuses.get(i, "ok") != "ok" else t)
        for i, t in mapping.items()
    )
    return Transcripts(
        recognizer=rec,
        engine=engine or {"name": "fake", "engine_version": "fake-1", "model_id": "fake",
                          "spanish_variant": "none", "streaming_granularity": "chunk",
                          "voice": {"name": "default", "kind": "fixed_voice", "checksum": None}},
        corpus=corpus_dict or {"corpus_version": "t", "corpus_hash": "h", "subset": "main", "limit": None},
        manifest_sha256="x", command="", environment={}, transcripts=items,
    )


def reference_of(s):
    return s.spoken if s.spoken is not None else s.text
