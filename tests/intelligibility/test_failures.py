import pytest

from tts_bench.corpus import Corpus
from tts_bench.intelligibility.scoring import score_transcripts

from .conftest import fixed_transcripts, reference_of


def one(corpus, status, text=""):
    s = corpus.sentences[0]
    r = score_transcripts(fixed_transcripts({s.id: text}, statuses={s.id: status}), Corpus("v", "h", (s,)))
    return r.sentences[0]


@pytest.mark.parametrize("status,flag", [("skipped_failed", "synthesis_failed"), ("skipped_silent", "silent_audio")])
def test_full_failure(corpus, status, flag):
    r = one(corpus, status)
    n_words = len(r.reference.split())
    assert r.primary["word"].rate == 1.0 and r.primary["word"].deletions == n_words
    assert r.primary["char"].rate == 1.0 and r.primary["char"].deletions == len(r.reference)
    assert flag in r.flags and r.counted_as_failure


def test_missing_transcript_is_full_failure(corpus):
    s = corpus.sentences[0]
    other = corpus.sentences[1]
    r = score_transcripts(fixed_transcripts({other.id: "x"}), Corpus("v", "h", (s,)))
    assert r.sentences[0].primary["word"].rate == 1.0 and "synthesis_failed" in r.sentences[0].flags


def test_empty_transcript_scored_normally_and_flagged(corpus):
    r = one(corpus, "ok", "")
    assert r.primary["word"].rate == 1.0 and "empty_transcript" in r.flags and not r.counted_as_failure


def test_reliable_threshold(corpus):
    ids = [s.id for s in corpus.sentences[:10]]
    sub = Corpus("v", "h", tuple(s for s in corpus.sentences if s.id in ids))
    texts = {i: reference_of(next(s for s in corpus.sentences if s.id == i)) for i in ids}
    one_flag = fixed_transcripts(texts, statuses={ids[0]: "skipped_failed"})
    assert score_transcripts(one_flag, sub).reliable            # exactly 10%
    two_flags = fixed_transcripts(texts, statuses={ids[0]: "skipped_failed", ids[1]: "skipped_silent"})
    assert not score_transcripts(two_flags, sub).reliable       # 20%
