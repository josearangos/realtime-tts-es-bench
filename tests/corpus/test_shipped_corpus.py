import time

from tts_bench.corpus import load_corpus
from tts_bench.corpus.loader import default_corpus_dir
from tts_bench.corpus.validate import validate


def test_shipped_corpus_validates_within_a_minute():
    start = time.monotonic()
    report = validate(default_corpus_dir())
    assert time.monotonic() - start < 60
    assert report.errors == [], [str(e) for e in report.errors]


def test_shipped_corpus_thresholds():
    c = load_corpus()
    assert len(c.sentences) >= 100
    for campaign in ("outbound_sales", "collections", "inbound"):
        assert len(c.by_campaign(campaign)) >= 25
    for tag in ("amount_cop", "number", "datetime", "acronym", "proper_name",
                "question", "long", "short", "hard_word"):
        assert len(c.by_tag(tag)) >= 10, tag


def test_cloning_subset_loads():
    assert len(load_corpus(subset="cloning").sentences) >= 15
