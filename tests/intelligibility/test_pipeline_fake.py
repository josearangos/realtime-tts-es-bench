import json

from tts_bench.intelligibility.files import read_manifest, read_results, write_results, write_transcripts
from tts_bench.intelligibility.model import NOTICE
from tts_bench.intelligibility.recognizer import FakeRecognizer
from tts_bench.intelligibility.scoring import score_transcripts
from tts_bench.intelligibility.synth import synthesize_corpus
from tts_bench.intelligibility.transcribe import transcribe_manifest

from .conftest import reference_of


def test_pipeline_end_to_end(tmp_path, make_adapter, voice, mini_corpus):
    corpus = mini_corpus(6)
    texts = [s.text for s in corpus.sentences]
    adapter = make_adapter(fail_texts=frozenset({texts[1]}), empty_texts=frozenset({texts[3]}))
    manifest = synthesize_corpus(adapter, corpus, voice, tmp_path / "audio", command="python -m tts_bench.intelligibility synthesize fake")
    statuses = {i.sentence_id: i.status for i in manifest.items}
    assert list(statuses.values()) == ["ok", "failed", "ok", "silent", "ok", "ok"]
    assert (tmp_path / "audio" / f"{corpus.sentences[0].id}.wav").is_file()
    assert read_manifest(tmp_path / "audio").items == manifest.items

    scripted = {s.id: reference_of(s) for s in corpus.sentences}
    scripted[corpus.sentences[2].id] = "texto equivocado"
    rec = FakeRecognizer(scripted)
    transcripts = transcribe_manifest(manifest, tmp_path / "audio", rec)
    assert sorted(rec.calls) == sorted(i.sentence_id for i in manifest.items if i.status == "ok")
    assert {t.sentence_id: t.status for t in transcripts.transcripts}[corpus.sentences[1].id] == "skipped_failed"
    assert {t.sentence_id: t.status for t in transcripts.transcripts}[corpus.sentences[3].id] == "skipped_silent"

    write_transcripts(transcripts, tmp_path / "t.json")
    results = score_transcripts(transcripts, corpus, command="python -m tts_bench.intelligibility score t.json")
    write_results(results, tmp_path / "r.json")
    loaded = read_results(tmp_path / "r.json")
    assert len(loaded.sentences) == 6 and loaded.overall.n_sentences == 6
    by = {s.sentence_id: s for s in loaded.sentences}
    assert by[corpus.sentences[1].id].counted_as_failure and by[corpus.sentences[3].id].counted_as_failure
    assert by[corpus.sentences[0].id].primary["word"].errors == 0
    assert by[corpus.sentences[2].id].primary["word"].errors > 0
    assert 0 < loaded.overall.primary["word"].rate < 1

    raw = (tmp_path / "r.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert ".wav" not in raw and str(tmp_path) not in raw          # no audio or voice material paths
    r = data["recognizer"]
    assert r["name"] == "fake" and r["checkpoint"] and r["settings"] and "library_versions" in r
    assert data["engine"]["spanish_variant"] and r["accent_note"]
    assert data["command"] and set(data["environment"]) >= {"python", "os_name", "os_release", "tts_bench_version", "git_commit"}
    assert "hostname" not in raw and data["notice"] == NOTICE
