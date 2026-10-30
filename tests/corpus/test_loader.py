import json

import pytest

from tts_bench.corpus import CorpusError, corpus_stamp, load_corpus
from tests.corpus.conftest import record, write_jsonl


def test_sentences_ordered_by_id(small_corpus):
    c = load_corpus(small_corpus)
    assert [s.id for s in c.sentences] == ["VEN-001", "VEN-002"]
    assert c.version == "0.1.0"


def test_cloning_subset_loads_separately(small_corpus):
    c = load_corpus(small_corpus, subset="cloning")
    assert [s.id for s in c.sentences] == ["CLO-001"]


def test_malformed_line_error_includes_line_number(small_corpus):
    p = small_corpus / "sentences.jsonl"
    p.write_text(p.read_text(encoding="utf-8") + "{not json}\n", encoding="utf-8")
    with pytest.raises(CorpusError, match=r"sentences\.jsonl:3"):
        load_corpus(small_corpus)


def test_unknown_enum_rejected(small_corpus):
    write_jsonl(small_corpus / "sentences.jsonl", [record(campaign="telemarketing")])
    with pytest.raises(CorpusError, match="unknown campaign"):
        load_corpus(small_corpus)


def test_missing_field_rejected(small_corpus):
    bad = record()
    del bad["probes"]
    write_jsonl(small_corpus / "sentences.jsonl", [bad])
    with pytest.raises(CorpusError, match="missing field.*probes"):
        load_corpus(small_corpus)


def test_hash_changes_when_text_changes(small_corpus):
    before = load_corpus(small_corpus).content_hash
    write_jsonl(small_corpus / "sentences.jsonl", [record("VEN-001", "Otro texto.")])
    assert load_corpus(small_corpus).content_hash != before


def test_hash_is_stable(small_corpus):
    assert load_corpus(small_corpus).content_hash == load_corpus(small_corpus).content_hash


def test_corpus_stamp_has_version_and_hash(small_corpus):
    c = load_corpus(small_corpus)
    assert corpus_stamp(c) == {"corpus_version": "0.1.0", "corpus_hash": c.content_hash}


def test_filters(small_corpus):
    c = load_corpus(small_corpus)
    assert len(c.by_campaign("outbound_sales")) == 2
    assert c.by_campaign("collections") == ()
    assert len(c.by_scenario("mobile_prepaid")) == 2
    assert c.by_tag("long") == ()


def test_bad_version_rejected(small_corpus):
    (small_corpus / "VERSION.json").write_text(json.dumps(
        {"version": "one", "date": "x", "counts": {}, "content_sha256": ""}), encoding="utf-8")
    with pytest.raises(CorpusError, match="MAJOR.MINOR.PATCH"):
        load_corpus(small_corpus)
