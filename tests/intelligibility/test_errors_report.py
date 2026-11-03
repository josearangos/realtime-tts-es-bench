from tts_bench.corpus import Corpus
from tts_bench.intelligibility.compare import error_report
from tts_bench.intelligibility.model import NOTICE
from tts_bench.intelligibility.scoring import score_transcripts

from .conftest import fixed_transcripts


def build(corpus):
    ids = ["COB-002", "COB-005", "COB-009", "VEN-031"]
    sub = Corpus(corpus.version, corpus.content_hash, tuple(s for s in corpus.sentences if s.id in ids))
    by = {s.id: s for s in sub.sentences}
    sp = lambda i: (by[i].spoken or by[i].text)
    texts = {
        "COB-002": sp("COB-002").replace("saldo", "salto"),                 # one substitution
        "COB-005": " ".join(sp("COB-005").split()[1:]),                     # one deletion
        "COB-009": sp("COB-009") + " extra",                                # one insertion
        "VEN-031": by["VEN-031"].text,                                      # exact
    }
    return score_transcripts(fixed_transcripts(texts), sub)


def test_lists_exact_words(corpus):
    out = error_report(build(corpus))
    assert out.startswith("> " + NOTICE)
    assert "substitution: saldo → salto" in out
    assert "deletion: " in out and "insertion: extra" in out
    assert "VEN-031" not in out                      # zero errors omitted


def test_sentence_filter_shows_zero_errors_when_selected(corpus):
    out = error_report(build(corpus), sentence="VEN-031")
    assert "VEN-031" in out and "COB-002" not in out


def test_tag_filter(corpus):
    out = error_report(build(corpus), tag="amount_cop")
    assert "COB-002" in out and "COB-009" in out and "VEN-031" not in out


def test_worst_orders_by_errors_then_id(corpus):
    r = build(corpus)
    out = error_report(r, worst=2)
    heads = [l for l in out.splitlines() if l.startswith("### ")]
    assert len(heads) == 2 and heads == sorted(heads)   # all tie at one error: id order
