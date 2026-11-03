import json

from tts_bench.intelligibility.files import read_manifest
from tts_bench.intelligibility.recognizer import FakeRecognizer
from tts_bench.intelligibility.scoring import score_transcripts
from tts_bench.intelligibility.synth import synthesize_corpus
from tts_bench.intelligibility.transcribe import transcribe_manifest

from .conftest import fixed_transcripts, reference_of


def test_score_twice_identical(corpus):
    tr = fixed_transcripts({s.id: reference_of(s)[:-6] for s in corpus.sentences})
    a, b = score_transcripts(tr, corpus), score_transcripts(tr, corpus)
    assert json.dumps(a.summary_dict(), sort_keys=True) == json.dumps(b.summary_dict(), sort_keys=True)
    assert [s.to_dict() for s in a.sentences] == [s.to_dict() for s in b.sentences]


def test_cache_hit_and_miss(tmp_path, make_adapter, voice, mini_corpus):
    corpus = mini_corpus(3)
    manifest = synthesize_corpus(make_adapter(), corpus, voice, tmp_path / "audio")
    scripted = {s.id: "hola" for s in corpus.sentences}
    cache = tmp_path / "cache"
    first = FakeRecognizer(scripted)
    transcribe_manifest(manifest, tmp_path / "audio", first, cache)
    assert len(first.calls) == 1   # the fake engine gives identical audio: one hash, one run
    second = FakeRecognizer(scripted)
    out = transcribe_manifest(manifest, tmp_path / "audio", second, cache)
    assert second.calls == [] and all(t.text == "hola" for t in out.transcripts)
    third = FakeRecognizer(scripted)
    third._settings = {"language": "es", "model": "fake", "beam_size": 5}   # different settings hash
    transcribe_manifest(manifest, tmp_path / "audio", third, cache)
    assert len(third.calls) == 1   # new settings hash: cache miss
