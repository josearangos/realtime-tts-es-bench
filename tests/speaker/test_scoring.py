import math
import statistics

import pytest

from tts_bench.speaker.scoring import score_embeddings

from .conftest import fixed_embeddings


def vec(c):
    """Unit vector whose cosine with the reference (1, 0, 0) is c."""
    return (c, math.sqrt(1 - c * c), 0.0)


def test_per_sentence_similarity_is_the_hand_computed_cosine(mini_corpus):
    corpus = mini_corpus(3)
    ids = [s.id for s in corpus.sentences]
    emb = fixed_embeddings({ids[0]: (3, 4, 0), ids[1]: (1, 0, 0), ids[2]: (0, 1, 0)})
    r = score_embeddings(emb, corpus)
    assert [s.similarity for s in r.sentences] == pytest.approx([0.6, 1.0, 0.0])
    assert r.sentences[0].campaign and isinstance(r.sentences[0].tags, tuple)


def test_only_the_designated_repetition_feeds_the_headline(mini_corpus):
    corpus = mini_corpus(2)
    a, b = (s.id for s in corpus.sentences)
    base = {(a, 1): vec(0.9), (b, 1): vec(0.7)}
    other = {**base, (a, 2): vec(0.1), (b, 2): vec(0.2), (a, 3): vec(0.3), (b, 3): vec(0.4)}
    r1 = score_embeddings(fixed_embeddings(base, repetitions=1), corpus)
    r3 = score_embeddings(fixed_embeddings(other, repetitions=3), corpus)
    assert r1.summary.similarity == r3.summary.similarity
    assert [s.similarity for s in r1.sentences] == [s.similarity for s in r3.sentences]


def test_engine_mean_sd_min_max_and_sample_sizes(mini_corpus):
    corpus = mini_corpus(4)
    values = [0.9, 0.8, 0.7, 0.6]
    emb = fixed_embeddings({s.id: vec(v) for s, v in zip(corpus.sentences, values)})
    r = score_embeddings(emb, corpus)
    st = r.summary.similarity
    assert st["mean"] == pytest.approx(0.75)
    assert st["sd"] == pytest.approx(statistics.stdev(values))
    assert (st["min"], st["max"]) == (pytest.approx(0.6), pytest.approx(0.9))
    assert (r.summary.n_sentences, r.summary.n_scored, r.summary.n_flagged) == (4, 4, 0)
    assert r.summary.status == "scored"


def test_identical_audio_near_max_and_different_speaker_clearly_lower(mini_corpus):
    corpus = mini_corpus(2)
    same, other = (s.id for s in corpus.sentences)
    r = score_embeddings(fixed_embeddings({same: (1, 0, 0), other: (0.2, 1, 0)}), corpus)
    sims = {s.sentence_id: s.similarity for s in r.sentences}
    assert sims[same] >= 0.99
    assert sims[same] - sims[other] >= 0.20


def test_single_scored_sentence_has_no_sd(mini_corpus):
    corpus = mini_corpus(1)
    r = score_embeddings(fixed_embeddings({corpus.sentences[0].id: vec(0.8)}), corpus)
    assert r.summary.similarity["sd"] is None
