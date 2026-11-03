import pytest

from tts_bench.metrics.runner import measure_request, run_repetitions


def _loaded(make_adapter, **kw):
    a = make_adapter(**kw)
    a.load()
    return a


def test_known_figures_chunk(make_adapter, voice, mini_corpus):
    a = _loaded(make_adapter, granularity="chunk", first_chunk_delay_s=0.2, chunk_interval_s=0.05,
                n_chunks=4, audio_seconds=1.0)
    corpus = mini_corpus(1)
    ms, windows = run_repetitions(a, corpus, voice, 1)
    m = ms[0]
    assert m.status == "ok"
    assert m.ttfa_ms == pytest.approx(200, rel=0.05)
    assert m.generation_ms == pytest.approx(350, rel=0.05)
    assert m.rtf == pytest.approx(0.35, rel=0.05)
    assert m.audio_seconds == pytest.approx(1.0)
    assert 1.0 / windows[1] == pytest.approx(1 / 0.35, rel=0.05)


def test_chunk_timings(make_adapter, voice, mini_corpus):
    a = _loaded(make_adapter, first_chunk_delay_s=0.05, chunk_interval_s=0.03, n_chunks=3)
    m = measure_request(a, mini_corpus(1).sentences[0], voice, 1, "steady")
    assert [c.index for c in m.chunks] == [0, 1, 2]
    assert m.chunks[0].gap_ms == m.chunks[0].at_ms
    assert m.chunks[1].gap_ms == pytest.approx(m.chunks[1].at_ms - m.chunks[0].at_ms)
    assert m.chunks[1].gap_ms == pytest.approx(30, rel=0.3)


def test_granularity_none(make_adapter, voice, mini_corpus):
    a = _loaded(make_adapter, granularity="none")
    m = measure_request(a, mini_corpus(1).sentences[0], voice, 1, "steady")
    assert m.status == "ok" and m.ttfa_ms is None and m.chunks == ()


def test_granularity_sentence(make_adapter, voice, mini_corpus):
    a = _loaded(make_adapter, granularity="sentence", first_chunk_delay_s=0.1)
    m = measure_request(a, mini_corpus(1).sentences[0], voice, 1, "steady")
    assert m.ttfa_ms == pytest.approx(100, rel=0.2)
    assert a.descriptor.streaming.granularity == "sentence"


def test_ttfa_ignores_empty_first_chunk(make_adapter, voice, mini_corpus):
    a = _loaded(make_adapter, empty_first_chunk=True, first_chunk_delay_s=0.05, chunk_interval_s=0.05)
    m = measure_request(a, mini_corpus(1).sentences[0], voice, 1, "steady")
    # the empty chunk arrives at ~50 ms, the first real one immediately after it
    assert m.chunks[0].at_ms < m.chunks[1].at_ms
    assert m.ttfa_ms == pytest.approx(m.chunks[1].at_ms)


def test_failed_and_invalid_sentences(make_adapter, voice, mini_corpus):
    corpus = mini_corpus(3)
    a = _loaded(make_adapter, first_chunk_delay_s=0.0, chunk_interval_s=0.0,
                fail_texts=frozenset({corpus.sentences[0].text}),
                empty_texts=frozenset({corpus.sentences[1].text}))
    ms, _ = run_repetitions(a, corpus, voice, 1)
    assert [m.status for m in ms] == ["failed", "invalid", "ok"]
    assert ms[0].error and "fake engine failure" in ms[0].error
    assert ms[1].rtf is None and ms[1].audio_seconds is None


def test_corpus_order(make_adapter, voice, mini_corpus):
    corpus = mini_corpus(4)
    a = _loaded(make_adapter, first_chunk_delay_s=0.0, chunk_interval_s=0.0)
    ms, _ = run_repetitions(a, corpus, voice, 2)
    ids = [s.id for s in corpus.sentences]
    assert [m.sentence_id for m in ms] == ids + ids
    assert [m.repetition for m in ms] == [1] * 4 + [2] * 4
