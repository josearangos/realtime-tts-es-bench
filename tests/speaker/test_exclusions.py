import pytest

from tts_bench.speaker.scoring import score_embeddings
from tts_bench.speaker.synth import not_applicable_message, synthesize_cloning

from .conftest import ENGINE, REFERENCE, fixed_embeddings


def test_non_cloning_engine_is_not_applicable(mini_corpus):
    emb = fixed_embeddings({}, engine={**ENGINE, "supports_cloning": False})
    r = score_embeddings(emb, mini_corpus(2))
    assert r.summary.status == "not_applicable"
    assert r.summary.similarity is None and r.sentences == () and r.consistency is None


def test_synthesize_writes_nothing_for_a_non_cloning_engine(tmp_path, make_adapter, mini_corpus, voice_ref, capsys):
    adapter = make_adapter(supports_cloning=False)
    out = tmp_path / "out"
    assert synthesize_cloning(adapter, mini_corpus(2), voice_ref, out, reference_quality=REFERENCE) is None
    assert not out.exists()
    assert not_applicable_message("piper") == "not applicable: piper does not clone voices"


def test_cli_prints_not_applicable_and_exits_zero(tmp_path, capsys, monkeypatch):
    from tts_bench.speaker.__main__ import main
    from tts_bench.core.registry import register

    register("fake-nocl", "tts_bench.adapters.fake:FakeAdapter")
    assert main(["synthesize", "fake-nocl", "--out", str(tmp_path / "o")]) == 0
    assert "not applicable: fake-nocl does not clone voices" in capsys.readouterr().out
    assert not (tmp_path / "o").exists()


def test_silent_and_failed_clips_are_excluded_and_counted(mini_corpus):
    corpus = mini_corpus(4)
    a, b, c, d = (s.id for s in corpus.sentences)
    emb = fixed_embeddings(
        {a: (1, 0, 0), b: None, c: None, d: (0.6, 0.8, 0)},
        statuses={b: "failed", c: "silent"})
    r = score_embeddings(emb, corpus)
    by = {s.sentence_id: s for s in r.sentences}
    assert by[b].flags == ("synthesis_failed",) and by[c].flags == ("silent_audio",)
    assert by[b].similarity is None and by[c].similarity is None
    assert (r.summary.n_scored, r.summary.n_flagged) == (2, 2)
    assert r.summary.similarity["mean"] == pytest.approx(0.8)


def test_short_audio_is_flagged_but_still_scored(mini_corpus):
    corpus = mini_corpus(3)
    a, b, c = (s.id for s in corpus.sentences)
    emb = fixed_embeddings({a: (1, 0, 0), b: (1, 0, 0), c: (1, 0, 0)}, durations={a: 2.99, b: 3.0, c: 1.0})
    r = score_embeddings(emb, corpus)
    by = {s.sentence_id: s for s in r.sentences}
    assert by[a].flags == ("short_audio",) and by[c].flags == ("short_audio",)
    assert by[b].flags == ()                      # exactly 3.0 s is not short
    assert r.summary.n_scored == 3 and r.summary.n_flagged == 0 and r.summary.n_short_audio == 2
    assert any("2 clip(s) shorter than 3.0 s" in w for w in r.summary.warnings)


def test_zero_norm_embedding_is_a_failure_flag_not_a_score(mini_corpus):
    corpus = mini_corpus(2)
    a, b = (s.id for s in corpus.sentences)
    r = score_embeddings(fixed_embeddings({a: (0, 0, 0), b: (1, 0, 0)}), corpus)
    by = {s.sentence_id: s for s in r.sentences}
    assert by[a].similarity is None and by[a].flags == ("embedding_failed",)
    assert r.summary.n_scored == 1 and r.summary.n_flagged == 1


def test_missing_designated_clip_counts_as_failed(mini_corpus):
    corpus = mini_corpus(2)
    r = score_embeddings(fixed_embeddings({corpus.sentences[0].id: (1, 0, 0)}), corpus)
    assert r.sentences[1].flags == ("synthesis_failed",)
