from tts_bench.evaluation import qc, tasks


def test_qc_shares_within_rounding(prepared):
    c = prepared.batch["counts"]
    n_test = c["mos"] + c["cmos"] + c["sim"]
    assert abs(c["repeats"] - 0.10 * n_test) <= 3          # one rounding step per project
    assert abs(c["attention"] - 0.10 * n_test) <= 3


def test_repeats_reference_existing_item_with_new_audio(prepared):
    by_id = {r.item_id: r for r in prepared.mapping}
    reps = [r for r in prepared.mapping if r.role == "repeat"]
    assert reps
    for r in reps:
        orig = by_id[r.repeat_of]
        assert orig.role == "test" and orig.sentence_id == r.sentence_id and orig.project == r.project
        assert r.item_id != orig.item_id and not set(r.served_files) & set(orig.served_files)
        x = (prepared.out / "served" / r.served_files[0]).read_bytes()
        y = (prepared.out / "served" / orig.served_files[0]).read_bytes()
        assert x == y  # same audio, new opaque file


def test_qc_items_have_no_distinguishing_field(prepared):
    for project, rows in prepared.tasks.items():
        assert all(set(d) == tasks.TASK_KEYS[project] for d in rows)
    roles = {r.role for r in prepared.mapping}
    assert {"test", "repeat", "attention_instructed", "attention_degraded"} <= roles


def test_attention_expectations(prepared):
    for r in prepared.mapping:
        if r.role.startswith("attention"):
            assert r.expected
        if r.role == "attention_degraded" and r.project == "mos":
            assert all(v == [1, 2] for v in r.expected.values())


def test_n_qc_edges():
    assert qc.n_qc(0, 0.1) == 0 and qc.n_qc(50, 0) == 0 and qc.n_qc(3, 0.05) == 1
