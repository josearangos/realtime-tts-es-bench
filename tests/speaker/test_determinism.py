import json
import math

import numpy as np

from tts_bench.speaker.embed import embed_directory
from tts_bench.speaker.embedder import FakeEmbedder
from tts_bench.speaker.pairs import compute_eer
from tts_bench.speaker.scoring import score_embeddings

from .conftest import fixed_embeddings, tone_audio, write_wav


def test_score_twice_is_byte_identical(mini_corpus):
    corpus = mini_corpus(3)
    mapping = {(s.id, rep): (math.cos(0.1 * rep + i), math.sin(0.1 * rep + i), 0.2)
               for i, s in enumerate(corpus.sentences) for rep in (1, 2, 3)}
    other = fixed_embeddings({"X": (0, 1, 0)}, reference=(0, 1, 0), reference_sha="b")
    emb = fixed_embeddings(mapping, repetitions=3)

    def dump():
        r = score_embeddings(emb, corpus, eer=compute_eer([emb, other])).to_dict()
        return json.dumps({k: r[k] for k in ("summary", "sentences", "consistency", "eer")}, sort_keys=True)

    assert dump() == dump()


def make_audio_dir(tmp_path):
    from tts_bench.speaker.files import write_manifest
    from tts_bench.speaker.model import Manifest, ManifestItem
    from tts_bench.speaker.files import sha256_file
    from .conftest import CORPUS, ENGINE, REFERENCE

    d = tmp_path / "audio"
    d.mkdir()
    write_wav(d / "S1-r1.wav", tone_audio(3.5, 16000, 440.0))
    item = ManifestItem("S1", 1, "S1-r1.wav", "ok", None, 16000, 3.5, sha256_file(d / "S1-r1.wav"))
    write_manifest(Manifest(ENGINE, CORPUS, 1, 1, REFERENCE, "", {}, (item,)), d)
    return d, write_wav(tmp_path / "ref.wav", tone_audio(3.5, 16000, 300.0))


def test_cache_hit_skips_the_embedder_and_a_new_settings_hash_misses(tmp_path):
    d, ref = make_audio_dir(tmp_path)
    cache = tmp_path / "cache"
    first = FakeEmbedder()
    a = embed_directory(d, first, reference_wav=ref, cache_dir=cache)
    assert first.calls == 2
    second = FakeEmbedder()
    b = embed_directory(d, second, reference_wav=ref, cache_dir=cache)
    assert second.calls == 0 and a.clips == b.clips and a.reference_vector == b.reference_vector

    class OtherSettings(FakeEmbedder):
        def record(self):
            import dataclasses
            r = super().record()
            return dataclasses.replace(r, settings={**r.settings, "dimension": 99}, settings_hash="changed")

    third = OtherSettings()
    embed_directory(d, third, reference_wav=ref, cache_dir=cache)
    assert third.calls == 2
