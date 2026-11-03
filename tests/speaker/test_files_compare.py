import dataclasses

import pytest

from tts_bench.speaker.compare import MergeRefused, compare_results
from tts_bench.speaker.files import FileFormatError, read_results, write_results
from tts_bench.speaker.model import NOTICE, EERRecord
from tts_bench.speaker.scoring import score_embeddings

from .conftest import ENGINE, fixed_embeddings


def result(corpus, *, name="fake", embedder=None, corpus_stamp=None, quality=None, cloning=True, eer=None):
    engine = {**ENGINE, "name": name, "supports_cloning": cloning}
    emb = fixed_embeddings({s.id: (1, 0.2, 0) for s in corpus.sentences}, engine=engine, embedder=embedder,
                           corpus=corpus_stamp, reference_quality=quality)
    return score_embeddings(emb, corpus, eer=eer)


def test_compare_same_conditions_succeeds_and_starts_with_notice(mini_corpus):
    corpus = mini_corpus(2)
    out = compare_results([result(corpus, name="a"), result(corpus, name="b")])
    assert out.startswith("> " + NOTICE)
    assert "| a |" in out and "| b |" in out


def test_non_cloning_engine_is_a_not_applicable_row(mini_corpus):
    corpus = mini_corpus(2)
    out = compare_results([result(corpus, name="a"), result(corpus, name="piper", cloning=False)])
    row = next(line for line in out.splitlines() if line.startswith("| piper"))
    assert "not applicable" in row and "does not clone" in row


@pytest.mark.parametrize("field", ["name", "checkpoint", "settings", "corpus_hash", "reference"])
def test_different_conditions_are_refused_naming_the_field(mini_corpus, field):
    from tts_bench.speaker.embedder import FakeEmbedder

    corpus = mini_corpus(2)
    base = FakeEmbedder().record()
    kw = {}
    if field == "name":
        kw["embedder"] = dataclasses.replace(base, name="other")
    elif field == "checkpoint":
        kw["embedder"] = dataclasses.replace(base, checkpoint="v2")
    elif field == "settings":
        kw["embedder"] = dataclasses.replace(base, settings={**base.settings, "sample_rate": 8000})
    elif field == "corpus_hash":
        kw["corpus_stamp"] = {"corpus_version": "t", "corpus_hash": "zzz", "subset": "cloning", "limit": None}
    else:
        from tts_bench.speaker.model import ReferenceQuality
        kw["quality"] = ReferenceQuality("rec-other", 1.0, 1.0, 1.0, "es-CO", ())
    with pytest.raises(MergeRefused) as err:
        compare_results([result(corpus), result(corpus, **kw)])
    assert field.replace("reference", "recording_id").split("_")[0] in err.value.field


def test_settings_hash_difference_is_refused(mini_corpus):
    from tts_bench.speaker.embedder import FakeEmbedder

    corpus = mini_corpus(1)
    other = dataclasses.replace(FakeEmbedder().record(), settings_hash="different")
    with pytest.raises(MergeRefused):
        compare_results([result(corpus), result(corpus, embedder=other)])


def test_different_hardware_does_not_block(mini_corpus):
    corpus = mini_corpus(1)
    a, b = result(corpus, name="a"), result(corpus, name="b")
    b = dataclasses.replace(b, environment={"os_name": "Linux", "cpu": "other"})
    assert compare_results([a, b])


def test_cli_compare_exits_3_on_a_refused_merge(tmp_path, mini_corpus, capsys):
    from tts_bench.speaker.__main__ import main

    corpus = mini_corpus(1)
    bad = {"corpus_version": "t", "corpus_hash": "zzz", "subset": "cloning", "limit": None}
    write_results(result(corpus), tmp_path / "a.json")
    write_results(result(corpus, corpus_stamp=bad), tmp_path / "b.json")
    assert main(["compare", str(tmp_path / "a.json"), str(tmp_path / "b.json")]) == 3
    assert "corpus_hash" in capsys.readouterr().err


def test_unknown_schema_version_is_refused(tmp_path, mini_corpus):
    p = tmp_path / "r.json"
    write_results(result(mini_corpus(1)), p)
    p.write_text(p.read_text(encoding="utf-8").replace('"schema_version": 1', '"schema_version": 99', 1),
                 encoding="utf-8")
    with pytest.raises(FileFormatError, match="unknown schema_version"):
        read_results(p)


def test_failed_gate_marks_results_not_reliable_for_ranking(mini_corpus):
    corpus = mini_corpus(1)
    bad = EERRecord(True, 0.25, 0.5, 4, 4, True, 0.1, False, None, "text")
    out = compare_results([result(corpus, eer=bad)])
    assert "Not reliable for ranking" in out and "interpreted cautiously" in out and "FAILED" in out
    good = EERRecord(True, 0.0, 0.5, 4, 4, False, 0.5, True, None, "text")
    ok = compare_results([result(corpus, eer=good)])
    assert "Not reliable" not in ok and "passed" in ok and "es-CO" in ok


def test_missing_eer_is_called_out(mini_corpus):
    assert "has not been run" in compare_results([result(mini_corpus(1))])


def test_consistency_table_declines_or_marks_unavailable(mini_corpus):
    corpus = mini_corpus(1)
    out = compare_results([result(corpus)])           # one repetition only
    assert "not available" in out
