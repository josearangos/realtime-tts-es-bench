import dataclasses

import pytest

from tts_bench.intelligibility.__main__ import main
from tts_bench.intelligibility.compare import MixedResultsError, compare_results
from tts_bench.intelligibility.files import FileFormatError, read_results, write_results
from tts_bench.intelligibility.model import NOTICE
from tts_bench.intelligibility.scoring import score_transcripts
from tts_bench.corpus import Corpus

from .conftest import fixed_transcripts, reference_of


@pytest.fixture
def results(corpus):
    sub = Corpus(corpus.version, corpus.content_hash, corpus.sentences)
    tr = fixed_transcripts({s.id: reference_of(s) for s in sub.sentences},
                           corpus_dict={"corpus_version": corpus.version, "corpus_hash": corpus.content_hash, "subset": "main", "limit": None})
    return score_transcripts(tr, sub)


def variant(r, **changes):
    return dataclasses.replace(r, **changes)


def test_same_recognizer_compares(results):
    other = variant(results, engine={**results.engine, "name": "other"})
    out = compare_results([results, other])
    assert out.startswith("> " + NOTICE) and "other" in out


@pytest.mark.parametrize("mutate,field", [
    (lambda r: variant(r, recognizer=dataclasses.replace(r.recognizer, checkpoint="x")), "recognizer.checkpoint"),
    (lambda r: variant(r, recognizer=dataclasses.replace(r.recognizer, library_versions={"faster-whisper": "9"})), "recognizer.library_versions"),
    (lambda r: variant(r, recognizer=dataclasses.replace(r.recognizer, settings={**r.recognizer.settings, "beam_size": 5})), "recognizer.settings.beam_size"),
    (lambda r: variant(r, normalization=dataclasses.replace(r.normalization, ruleset_version="2")), "normalization.ruleset_version"),
    (lambda r: variant(r, corpus={**r.corpus, "corpus_hash": "zz"}), "corpus.corpus_hash"),
    (lambda r: variant(r, corpus={**r.corpus, "subset": "cloning"}), "corpus.subset"),
    (lambda r: variant(r, corpus={**r.corpus, "limit": 5}), "corpus.limit"),
])
def test_refuses_mixed(results, mutate, field):
    with pytest.raises(MixedResultsError) as e:
        compare_results([results, mutate(results)])
    assert e.value.field == field and field in str(e.value)


def test_hardware_difference_does_not_block(results):
    other = variant(results, environment={**results.environment, "os_release": "99"})
    assert "Environments differ" in compare_results([results, other])


def test_cli_exit_3_and_schema(tmp_path, results):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    write_results(results, a)
    write_results(variant(results, recognizer=dataclasses.replace(results.recognizer, checkpoint="x")), b)
    assert main(["compare", str(a), str(b)]) == 3
    assert main(["compare", str(a)]) == 0
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version": 99}')
    with pytest.raises(FileFormatError):
        read_results(bad)
    assert main(["compare", str(a), str(bad)]) == 3


def test_group_tables(results, corpus):
    out = compare_results([results])
    assert "## Per tag" in out and "## Per campaign" in out
    for t in {t.value for s in corpus.sentences for t in s.tags}:
        assert f"tag:{t}" in out
    assert "low sample" in out and "overlap" in out
