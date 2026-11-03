"""Needs the real embedding model: run in .venv-spk with `pytest -m engine tests/speaker`."""

import numpy as np
import pytest

from .conftest import tone_audio

pytestmark = pytest.mark.engine


@pytest.fixture(scope="module")
def embedder():
    pytest.importorskip("speechbrain")
    from tts_bench.speaker.embedder import SpeechBrainEmbedder

    return SpeechBrainEmbedder()


def clip(seed, seconds=4.0, rate=16000):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * rate)) / rate
    f0 = 100 + 40 * seed
    x = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 8)) * 0.1
    return (x + rng.normal(0, 0.002, x.size)).astype(np.float32)


def test_same_clip_twice_is_identical_and_self_similarity_is_one(embedder):
    from tts_bench.speaker.similarity import cosine_similarity

    x = clip(1)
    a, b = embedder.embed(x, 16000), embedder.embed(x, 16000)
    assert a.shape == (192,)
    assert np.array_equal(a, b)
    assert cosine_similarity(a, b) >= 0.99


def test_record_names_the_model_and_versions(embedder):
    r = embedder.record()
    assert r.name == "speechbrain-ecapa" and "spkrec-ecapa-voxceleb" in r.checkpoint
    assert r.library_versions["speechbrain"] and r.settings["dimension"] == 192 and r.settings_hash


def test_two_consented_voices_separate_on_spanish_audio(embedder, tmp_path):
    """Spanish sanity check: same-voice clips score at least 0.20 above different-voice clips."""
    from pathlib import Path

    from tts_bench.speaker.embed import read_wav_mono
    from tts_bench.speaker.similarity import cosine_similarity
    from tts_bench.voices import LocalVoiceLibrary

    root = Path(__file__).resolve().parents[2] / "cloned_voices"
    if not (root / "library.json").is_file():
        pytest.skip("no local voice library")
    lib = LocalVoiceLibrary(root)
    recs = sorted(lib._load()["recordings"])
    if len(recs) < 2:
        pytest.skip("needs two consented recordings")
    vecs = {}
    for rid in recs[:2]:
        for k, (start, length) in enumerate(((0.0, 6.0), (7.0, 6.0))):
            wav = lib.prepare_segment(rid, "test", start, length, dest=tmp_path / f"{rid}-{k}.wav")
            samples, rate = read_wav_mono(wav)
            vecs[(rid, k)] = embedder.embed(samples, rate)
    a, b = recs[:2]
    same = [cosine_similarity(vecs[(a, 0)], vecs[(a, 1)]), cosine_similarity(vecs[(b, 0)], vecs[(b, 1)])]
    diff = [cosine_similarity(vecs[(a, i)], vecs[(b, j)]) for i in (0, 1) for j in (0, 1)]
    assert sum(same) / 2 - sum(diff) / 4 >= 0.20
