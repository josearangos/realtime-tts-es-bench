import json
import re

import pytest

from tts_bench.evaluation import blind, fakes, sources


def test_ids_format_unique_reproducible():
    a = blind.IdGenerator(blind.make_rng(7))
    ids = [a.new() for _ in range(2000)]
    assert all(re.fullmatch(r"[0-9a-f]{12}", i) for i in ids) and len(set(ids)) == 2000
    b = blind.IdGenerator(blind.make_rng(7))
    assert [b.new() for _ in range(2000)] == ids
    c = blind.IdGenerator(blind.make_rng(8))
    assert [c.new() for _ in range(5)] != ids[:5]


def test_mapping_roundtrip(tmp_path):
    rows = [blind.MappingRow("a" * 12, "cmos", engine="x", a={"engine": "x"}, b={"engine": "y"}, position="ba",
                             served_files=["a.wav"]),
            blind.MappingRow("b" * 12, "mos", role="repeat", repeat_of="c" * 12, expected=["x"])]
    path = tmp_path / "private" / "mapping.jsonl"
    blind.write_mapping(path, rows)
    assert blind.read_mapping(path) == rows


@pytest.fixture
def dataset(tmp_path):
    return fakes.make_fake_dataset(tmp_path)


def test_discovery_on_fake_dataset(dataset):
    corpus = sources.load_corpus_info(dataset["corpus"])
    clips = sources.discover(dataset["output"], corpus, voices_dir=dataset["voices_dir"])
    conds = {c.condition for c in clips}
    assert conds == {"fakea/voz1", "fakeb/voz2", "fakec/clon1"}
    cloned = [c for c in clips if c.cloned]
    assert cloned and all(c.reference_wav for c in cloned)
    assert corpus.version == "9.9.9" and len(corpus.content_sha256) == 64


def test_unknown_sentence_rejected(dataset, tmp_path):
    corpus = sources.load_corpus_info(dataset["corpus"])
    wav = next(dataset["output"].rglob("*.wav"))
    m = tmp_path / "m.jsonl"
    m.write_text(json.dumps({"engine": "e", "voice": "v", "sentence_id": "ZZZ-999", "wav": str(wav)}) + "\n")
    with pytest.raises(sources.SourceError, match="ZZZ-999"):
        sources.discover(dataset["output"], corpus, [m], voices_dir=dataset["voices_dir"])


def test_manifest_route(dataset, tmp_path):
    corpus = sources.load_corpus_info(dataset["corpus"])
    wav = next(dataset["output"].rglob("*.wav"))
    m = tmp_path / "m.jsonl"
    m.write_text(json.dumps({"engine": "e", "voice": "v", "accent": "es-AR", "sentence_id": dataset["main_ids"][0],
                             "wav": str(wav)}) + "\n")
    clips = sources.read_source_manifest(m)
    assert clips[0].accent == "es-AR" and not clips[0].cloned


def test_voice_without_human_evaluation_consent_is_excluded(tmp_path, capsys):
    from tts_bench.voices.consent import ConsentRecord
    from tts_bench.voices.library import LocalVoiceLibrary

    data = fakes.make_fake_dataset(tmp_path)
    lib = LocalVoiceLibrary(data["voices_dir"])
    lib.add_consent(ConsentRecord("fakeowner", "2025", ["internal_benchmarking"], ["collections", "cloning_prompts"]))
    corpus = sources.load_corpus_info(data["corpus"])
    clips = sources.discover(data["output"], corpus, voices_dir=data["voices_dir"])
    assert {c.condition for c in clips} == {"fakea/voz1", "fakeb/voz2"}  # the cloned voice is not used at all
    assert "excluded from human evaluation" in capsys.readouterr().err
