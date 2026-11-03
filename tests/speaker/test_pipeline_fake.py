import json

import numpy as np
import pytest

from tts_bench.core.voices import VoiceReference
from tts_bench.speaker.embed import embed_directory
from tts_bench.speaker.embedder import FakeEmbedder
from tts_bench.speaker.files import read_embeddings, read_manifest, read_results, write_results
from tts_bench.speaker.model import NOTICE
from tts_bench.speaker.reference import resolve_reference
from tts_bench.speaker.scoring import score_embeddings
from tts_bench.speaker.synth import synthesize_cloning


def run_pipeline(tmp_path, make_adapter, fake_voice_library, corpus, *, voice_name=None, repetitions=3, **adapter_kw):
    voice_name = voice_name or fake_voice_library.reference_voice
    ref_wav, quality = resolve_reference(fake_voice_library.lib, voice_name, engine="fake",
                                         use="internal_benchmarking", work_dir=tmp_path / "work")
    voice = VoiceReference(voice_name, "reference_audio", "memory://v")
    out = tmp_path / "audio"
    manifest = synthesize_cloning(
        make_adapter(**adapter_kw), corpus, voice, out, repetitions=repetitions, reference_quality=quality,
        voice_info={"name": voice_name, "kind": "reference_audio", "recording_id": quality.recording_id,
                    "accent_label": "es-CO"},
        command="python -m tts_bench.speaker synthesize fake")
    emb = embed_directory(out, FakeEmbedder(), reference_wav=ref_wav, command="python -m tts_bench.speaker embed")
    return out, manifest, emb, quality


def test_end_to_end_with_fakes(tmp_path, make_adapter, fake_voice_library, mini_corpus):
    corpus = mini_corpus(5)
    out, manifest, emb, quality = run_pipeline(tmp_path, make_adapter, fake_voice_library, corpus)
    assert len(manifest.items) == 15 and manifest.repetitions == 3 and manifest.designated_repetition == 1
    assert [i.repetition for i in manifest.items[:5]] == [1] * 5
    assert (out / f"{corpus.sentences[0].id}-r1.wav").is_file()
    assert read_manifest(out).items == manifest.items
    assert manifest.corpus["subset"] == "cloning"

    loaded = read_embeddings(out)
    assert loaded.embedder.name == "fake-embedder" and len(loaded.clips) == 15

    results = score_embeddings(loaded, corpus, command="python -m tts_bench.speaker score x",
                               environment={"python": "3"})
    write_results(results, tmp_path / "r.json")
    data = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert data["notice"] == NOTICE and data["audio_language"] == "es"
    e = data["embedder"]
    assert e["name"] and e["checkpoint"] and e["settings_hash"] and "library_versions" in e
    q = data["reference_quality"]
    assert q["recording_id"] == fake_voice_library.recording_id and q["accent"] == "es-CO"
    assert {"duration_s", "speech_seconds", "snr_estimate_db", "warnings"} <= set(q)
    assert data["corpus"]["subset"] == "cloning" and data["engine"]["name"] == "fake"
    assert data["command"] and data["environment"]
    assert len(data["sentences"]) == 5 and data["consistency"]["repetitions"] == 3
    assert read_results(tmp_path / "r.json").summary == results.summary


def test_reference_comes_from_the_library_for_both_voice_kinds(tmp_path, fake_voice_library):
    for name in (fake_voice_library.reference_voice, fake_voice_library.stored_voice):
        wav, q = resolve_reference(fake_voice_library.lib, name, engine="fake", use="internal_benchmarking",
                                   work_dir=tmp_path / name)
        assert wav.is_file() and wav.suffix == ".wav"
        assert q.recording_id == fake_voice_library.recording_id and q.accent == "es-CO"
        assert q.duration_s > 0 and q.speech_seconds > 0


def test_reference_refuses_without_consent_for_the_use(fake_voice_library):
    from tts_bench.core.errors import ConsentNotPermittedError

    with pytest.raises(ConsentNotPermittedError):
        resolve_reference(fake_voice_library.lib, fake_voice_library.reference_voice, engine="fake",
                          use="published_results")


def test_failed_and_silent_syntheses_are_recorded(tmp_path, make_adapter, fake_voice_library, mini_corpus):
    corpus = mini_corpus(3)
    texts = [s.text for s in corpus.sentences]
    _, manifest, emb, _ = run_pipeline(tmp_path, make_adapter, fake_voice_library, corpus, repetitions=2,
                                       fail_texts=frozenset({texts[1]}), empty_texts=frozenset({texts[2]}))
    status = {(i.sentence_id, i.repetition): i.status for i in manifest.items}
    assert status[(corpus.sentences[1].id, 1)] == "failed" and status[(corpus.sentences[2].id, 2)] == "silent"
    assert all(c.vector is None for c in emb.clips if c.status != "ok")
    r = score_embeddings(emb, corpus)
    assert r.summary.n_scored == 1 and r.summary.n_flagged == 2


def test_load_failure_writes_nothing(tmp_path, make_adapter, voice_ref, mini_corpus):
    from tts_bench.core.errors import TTSBenchError
    from .conftest import REFERENCE

    adapter = make_adapter()

    def boom():
        raise TTSBenchError("no weights")

    adapter._load = boom
    with pytest.raises(TTSBenchError):
        synthesize_cloning(adapter, mini_corpus(1), voice_ref, tmp_path / "o", reference_quality=REFERENCE)
    assert not (tmp_path / "o").exists()


def test_cli_end_to_end_with_the_fake_engine(tmp_path, fake_voice_library, monkeypatch, capsys):
    from tts_bench.speaker.__main__ import main

    lib_root = str(fake_voice_library.lib.root)
    base = ["--voices-dir", lib_root]
    out = str(tmp_path / "audio")
    assert main(["synthesize", "fake", "--voice", "voz-ref", "--repetitions", "2", "--limit", "3",
                 "--out", out, *base]) == 0
    audio = tmp_path / "audio" / "fake-voz-ref"
    assert (audio / "manifest.json").is_file()
    assert main(["embed", str(audio), "--model", "fake", *base]) == 0
    assert (audio / "embeddings.json").is_file()
    results_dir = str(tmp_path / "results")
    capsys.readouterr()
    assert main(["score", str(audio / "embeddings.json"), "--out", results_dir]) == 0
    printed = capsys.readouterr().out
    assert printed.startswith(NOTICE)
    (result,) = (tmp_path / "results").glob("fake-*.json")
    assert main(["compare", str(result), "--out", str(tmp_path / "c.md")]) == 0
    assert (tmp_path / "c.md").read_text(encoding="utf-8").startswith("> " + NOTICE)
    assert main(["score", str(tmp_path / "missing.json")]) == 1
