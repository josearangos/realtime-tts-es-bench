from tts_bench.evaluation.quality import compute_quality

TH = {"repeat_within_1_min": 0.7, "max_failed_checks": 1}


def rec(ann, item, ans, role="test", repeat_of=None, expected=None, project="mos"):
    return {"project": project, "item_id": item, "annotator_id": ann, "role": role, "repeat_of": repeat_of,
            "answers": ans, "expected": expected}


def mos(v):
    return {"naturalidad": v, "pronunciacion": v, "prosodia": v}


def test_consistent_attentive_annotator_not_flagged():
    recs = [rec("a01", "i1", mos(4)), rec("a01", "r1", mos(5), "repeat", "i1"),
            rec("a01", "i2", mos(3)), rec("a01", "r2", mos(3), "repeat", "i2"),
            rec("a01", "c1", mos(2), "attention_degraded", expected={k: [1, 2] for k in mos(0)}),
            rec("a01", "c2", mos(4), "attention_instructed", expected={k: [4] for k in mos(0)})]
    q = compute_quality(recs, TH)["annotators"]["a01"]
    assert not q["flagged"] and q["repeat_pairs"] == 2 and q["repeat_within_1"] == 1.0 and q["attention_failed"] == 0
    assert q["repeat_mad"] == 0.5 and q["n_annotations"] == 6


def test_failing_two_checks_is_flagged_with_reason():
    exp = {k: [1, 2] for k in mos(0)}
    recs = [rec("a02", f"c{i}", mos(5), "attention_degraded", expected=exp) for i in range(2)]
    q = compute_quality(recs, TH)["annotators"]["a02"]
    assert q["flagged"] and q["attention_failed"] == 2 and "attention" in q["reasons"][0]


def test_low_repeat_consistency_flagged():
    recs = []
    for i in range(4):
        recs += [rec("a03", f"i{i}", mos(1)), rec("a03", f"r{i}", mos(5), "repeat", f"i{i}")]
    q = compute_quality(recs, TH)["annotators"]["a03"]
    assert q["flagged"] and q["repeat_within_1"] == 0.0 and any("repeat" in r for r in q["reasons"])


def test_no_repeats_no_flag_and_thresholds_reported():
    out = compute_quality([rec("a04", "i", mos(3))], TH)
    assert out["annotators"]["a04"]["repeat_within_1"] is None and not out["annotators"]["a04"]["flagged"]
    assert out["thresholds"] == TH
