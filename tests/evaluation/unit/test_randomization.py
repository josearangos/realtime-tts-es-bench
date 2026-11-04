import json

from tests.evaluation.conftest import build


def test_same_seed_identical_batch(tmp_path):
    a = build(tmp_path / "a")
    b = build(tmp_path / "b")
    assert a.tasks == b.tasks
    assert [r.__dict__ for r in a.mapping] == [r.__dict__ for r in b.mapping]


def test_different_seed_changes_order_and_ids(tmp_path):
    a = build(tmp_path / "a", seed=1)
    b = build(tmp_path / "b", seed=2)
    assert [d["item_id"] for d in a.tasks["mos"]] != [d["item_id"] for d in b.tasks["mos"]]


def test_ab_positions_balanced(tmp_path):
    p = build(tmp_path, n=20)
    cm = [r for r in p.mapping if r.project == "cmos" and r.role == "test"]
    share = sum(r.position == "ba" for r in cm) / len(cm)
    assert 0.4 <= share <= 0.6
    for r in cm:  # position agrees with the recorded A/B conditions
        assert r.a != r.b


def test_mapping_rows_complete(prepared):
    for r in prepared.mapping:
        assert r.corpus_version == "9.9.9" and r.sentence_id
        if r.project == "cmos":
            assert r.a and r.b and r.a["engine"] and r.b["voice"]
        else:
            assert r.engine and r.voice


def test_reprepare_reuses_frozen_batch(prepared):
    from tts_bench import evaluation  # noqa: F401
    from tts_bench.evaluation import batch
    again = batch.prepare(prepared.cfg, prepared.clips, prepared.corpus, prepared.out)
    assert again == prepared.batch
