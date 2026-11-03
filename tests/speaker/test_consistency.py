import math
import statistics

import pytest

from tts_bench.speaker.scoring import score_embeddings

from .conftest import fixed_embeddings


def vec(c):
    return (c, math.sqrt(1 - c * c), 0.0)


def cv(values):
    return statistics.stdev(values) / statistics.fmean(values)


def test_duration_and_similarity_cv_match_hand_values(mini_corpus):
    corpus = mini_corpus(4)
    durs, sims = (3.0, 3.3, 2.7, 3.0, 3.0), (0.9, 0.8, 0.85, 0.7, 0.75)
    mapping, durations = {}, {}
    for s in corpus.sentences:
        for rep in range(1, 6):
            mapping[(s.id, rep)] = vec(sims[rep - 1])
            durations[(s.id, rep)] = durs[rep - 1]
    r = score_embeddings(fixed_embeddings(mapping, repetitions=5, durations=durations), corpus)
    c = r.consistency
    assert c.repetitions == 5
    assert c.duration["cv_median"] == pytest.approx(cv(durs), rel=0.05)
    assert c.similarity["cv_median"] == pytest.approx(cv(sims), rel=0.05)
    assert c.duration["n_sentences_valid"] == 4 and c.duration["cv_mean"] == pytest.approx(cv(durs))
    assert all(row["n"] == 5 and row["reason"] is None for row in c.per_sentence)


def test_engine_figure_is_the_median_of_sentence_cvs(mini_corpus):
    corpus = mini_corpus(3)
    spreads = {corpus.sentences[0].id: (4.0, 4.0), corpus.sentences[1].id: (4.0, 4.4),
               corpus.sentences[2].id: (4.0, 6.0)}
    mapping = {(sid, rep): (1, 0, 0) for sid in spreads for rep in (1, 2)}
    durations = {(sid, rep): d for sid, ds in spreads.items() for rep, d in zip((1, 2), ds)}
    c = score_embeddings(fixed_embeddings(mapping, repetitions=2, durations=durations), corpus).consistency
    expected = sorted(cv(ds) for ds in spreads.values())
    assert c.duration["cv_median"] == pytest.approx(expected[1])
    assert c.duration["cv_mean"] == pytest.approx(statistics.fmean(expected))


def test_single_repetition_is_unavailable_and_counted(mini_corpus):
    corpus = mini_corpus(2)
    a, b = (s.id for s in corpus.sentences)
    mapping = {(a, 1): (1, 0, 0), (a, 2): (1, 0, 0), (b, 1): (1, 0, 0), (b, 2): None}
    emb = fixed_embeddings(mapping, repetitions=2, statuses={(b, 2): "failed"})
    c = score_embeddings(emb, corpus).consistency
    rows = {r["sentence_id"]: r for r in c.per_sentence}
    assert rows[b]["reason"] == "fewer_than_two" and rows[b]["duration_cv"] is None and rows[b]["n"] == 1
    assert c.duration["n_unavailable"] == 1 and c.duration["n_sentences_valid"] == 1


def test_near_zero_similarity_mean_is_declined(mini_corpus):
    corpus = mini_corpus(2)
    a, b = (s.id for s in corpus.sentences)
    mapping = {(a, 1): (0, 1, 0), (a, 2): (0.01, 1, 0), (b, 1): vec(0.9), (b, 2): vec(0.8)}
    c = score_embeddings(fixed_embeddings(mapping, repetitions=2), corpus).consistency
    rows = {r["sentence_id"]: r for r in c.per_sentence}
    assert rows[a]["similarity_cv"] is None and rows[a]["reason"] == "near_zero_mean"
    assert c.similarity["n_declined"] == 1 and c.similarity["n_sentences_valid"] == 1
    assert c.similarity["cv_median"] == pytest.approx(cv([0.9, 0.8]))


def test_failed_and_silent_repetitions_are_left_out(mini_corpus):
    corpus = mini_corpus(1)
    a = corpus.sentences[0].id
    mapping = {(a, 1): (1, 0, 0), (a, 2): (1, 0, 0), (a, 3): None, (a, 4): None}
    emb = fixed_embeddings(mapping, repetitions=4, durations={(a, 1): 3.0, (a, 2): 3.3},
                           statuses={(a, 3): "failed", (a, 4): "silent"})
    row = score_embeddings(emb, corpus).consistency.per_sentence[0]
    assert row["n"] == 2 and row["duration_cv"] == pytest.approx(cv([3.0, 3.3]))


def test_consistency_with_the_fake_engine_at_known_durations(tmp_path, make_adapter, mini_corpus, voice_ref):
    from tts_bench.speaker.embed import embed_directory
    from tts_bench.speaker.synth import synthesize_cloning

    from .conftest import REFERENCE, tone_audio, write_wav

    corpus = mini_corpus(4)
    seq = (3.0, 3.3, 2.7, 3.0, 3.0)
    # 4 sentences x 5 repetitions; the call order is repetition-major, so each repetition
    # uses one duration for all four sentences only if the sequence repeats by sentence.
    adapter = make_adapter(audio_seconds_sequence=tuple(d for d in seq for _ in range(4)))
    out = tmp_path / "audio"
    manifest = synthesize_cloning(adapter, corpus, voice_ref, out, repetitions=5, reference_quality=REFERENCE)
    ref = write_wav(tmp_path / "ref.wav", tone_audio(3.0, 16000, 300.0))
    from tts_bench.speaker.embedder import FakeEmbedder
    emb = embed_directory(out, FakeEmbedder(), reference_wav=ref)
    c = score_embeddings(emb, corpus).consistency
    assert c.duration["cv_median"] == pytest.approx(cv(seq), rel=0.05)
    assert c.similarity["cv_median"] == pytest.approx(0.0, abs=1e-9)   # same tone each time
