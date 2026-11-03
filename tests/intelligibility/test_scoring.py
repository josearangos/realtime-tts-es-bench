import pytest

from tts_bench.corpus import Corpus
from tts_bench.intelligibility.scoring import score_transcripts

from .conftest import fixed_transcripts, reference_of


def sub_corpus(corpus, ids):
    return Corpus(corpus.version, corpus.content_hash, tuple(s for s in corpus.sentences if s.id in ids))


def test_per_sentence_hand_calculated(corpus):
    s = corpus.sentences[0]
    ref = reference_of(s).split()
    r = score_transcripts(fixed_transcripts({s.id: " ".join(ref[:-1])}), sub_corpus(corpus, {s.id}))
    w = r.sentences[0].primary["word"]
    assert (w.substitutions, w.deletions, w.insertions) == (0, 1, 0)
    assert r.sentences[0].reference == r.sentences[0].reference.lower()


def test_overall_is_pooled_not_mean(corpus):
    short = next(s for s in corpus.sentences if len(reference_of(s).split()) <= 4 and "?" not in s.text)
    long_ = max(corpus.sentences, key=lambda s: len(reference_of(s).split()))
    ids = {short.id, long_.id}
    # the short sentence is fully wrong, the long one exact
    tr = fixed_transcripts({short.id: "zzz", long_.id: reference_of(long_)})
    r = score_transcripts(tr, sub_corpus(corpus, ids))
    o = r.overall.primary["word"]
    n_short = len(r.sentences[0].reference.split()) if r.sentences[0].sentence_id == short.id else len(r.sentences[1].reference.split())
    n_long = sum(len(x.reference.split()) for x in r.sentences) - n_short
    assert o.errors == n_short  # S + D, no insertion
    assert o.rate == pytest.approx(n_short / (n_short + n_long))
    mean = sum(x.primary["word"].rate for x in r.sentences) / 2
    assert o.rate != pytest.approx(mean)


def test_empty_reference_flagged_and_excluded(corpus):
    from tts_bench.intelligibility.scoring import score_sentence
    from tts_bench.intelligibility.model import Transcript
    import dataclasses

    s = dataclasses.replace(corpus.sentences[0], text="¿?", spoken=None)
    res = score_sentence(s, Transcript(s.id, "x", "ok", "algo"))
    assert "empty_reference" in res.flags and res.primary["word"].rate is None


def test_reference_is_spoken_else_text(corpus):
    with_spoken = next(s for s in corpus.sentences if s.spoken)
    r = score_transcripts(fixed_transcripts({with_spoken.id: with_spoken.spoken}), sub_corpus(corpus, {with_spoken.id}))
    assert r.sentences[0].primary["word"].errors == 0
    plain = next(s for s in corpus.sentences if not s.spoken)
    r = score_transcripts(fixed_transcripts({plain.id: plain.text}), sub_corpus(corpus, {plain.id}))
    assert r.sentences[0].primary["word"].errors == 0


def test_groups_cover_every_campaign_and_tag(corpus):
    sub = Corpus(corpus.version, corpus.content_hash, corpus.sentences)
    tr = fixed_transcripts({s.id: reference_of(s) for s in sub.sentences})
    r = score_transcripts(tr, sub)
    names = {g.group for g in r.groups}
    assert "overall" in names
    assert {f"campaign:{s.campaign.value}" for s in sub.sentences} <= names
    assert {f"tag:{t.value}" for s in sub.sentences for t in s.tags} <= names
    assert r.overall.n_sentences == len(sub.sentences)
    assert r.overall.primary["word"].errors == 0


def test_two_tags_counted_in_both(corpus):
    s = next(x for x in corpus.sentences if len(x.tags) >= 2)
    r = score_transcripts(fixed_transcripts({s.id: "x"}), sub_corpus(corpus, {s.id}))
    for t in s.tags:
        assert r.group(f"tag:{t.value}").n_sentences == 1


def test_low_sample(corpus):
    ids = [s.id for s in corpus.sentences[:10]]
    r9 = score_transcripts(fixed_transcripts({i: "" for i in ids[:9]}), sub_corpus(corpus, set(ids[:9])))
    r10 = score_transcripts(fixed_transcripts({i: "" for i in ids}), sub_corpus(corpus, set(ids)))
    assert r9.overall.low_sample and not r10.overall.low_sample


def test_digits_reference_and_words_transcript_zero_errors(corpus):
    import dataclasses

    s = dataclasses.replace(corpus.sentences[0], text="Debe $20.000 el 5 de mayo", spoken=None)
    c = Corpus("v", "h", (s,))
    r = score_transcripts(fixed_transcripts({s.id: "Debe veinte mil pesos el cinco de mayo"}), c)
    assert r.sentences[0].primary["word"].errors == 0


def test_spoken_reference_and_digit_transcript_zero_errors(corpus):
    s = next(x for x in corpus.sentences if x.id == "COB-003")
    r = score_transcripts(fixed_transcripts({s.id: s.text}), sub_corpus(corpus, {s.id}))
    assert r.sentences[0].primary["word"].errors == 0 and r.sentences[0].number_readings == ("digits",)


def test_digit_reference_without_spoken_is_cardinal(corpus):
    import dataclasses

    s = dataclasses.replace(corpus.sentences[0], text="Tiene 21 cuotas", spoken=None)
    c = Corpus("v", "h", (s,))
    ok = score_transcripts(fixed_transcripts({s.id: "tiene veintiuno cuotas"}), c)
    assert ok.sentences[0].primary["word"].errors == 0
    digit = score_transcripts(fixed_transcripts({s.id: "tiene dos uno cuotas"}), c)
    assert digit.sentences[0].primary["word"].errors > 0


def test_accent_sensitive_higher_when_only_accent_differs(corpus):
    import dataclasses

    s = dataclasses.replace(corpus.sentences[0], text="Está pendiente", spoken=None)
    r = score_transcripts(fixed_transcripts({s.id: "esta pendiente"}), Corpus("v", "h", (s,)))
    assert r.overall.primary["word"].rate == 0
    assert r.overall.accent_sensitive["word"].rate == 0.5
