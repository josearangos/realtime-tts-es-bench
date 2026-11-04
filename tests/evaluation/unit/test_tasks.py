from tts_bench.evaluation import tasks


def test_counts_for_fake_dataset(prepared):
    # main group: 3 conditions, 6 sentences; cloned condition adds a SIM item per sentence
    c = prepared.batch["counts"]
    assert c["mos"] == 3 * 6 and c["cmos"] == 3 * 6 and c["sim"] == 6
    assert c["repeats"] >= 3 and c["attention"] >= 3


def test_same_sentences_for_every_condition(prepared):
    per_cond = {}
    for r in prepared.mapping:
        if r.project == "mos" and r.role == "test":
            per_cond.setdefault((r.engine, r.voice), set()).add(r.sentence_id)
    assert len(per_cond) == 3 and len({frozenset(v) for v in per_cond.values()}) == 1


def test_sim_only_for_cloned_voices_with_reference(prepared):
    sim = [r for r in prepared.mapping if r.project == "sim" and r.role in ("test", "repeat")]
    assert sim and all(r.cloned and len(r.served_files) == 2 for r in sim)


def test_task_data_keys_exactly_per_contract(prepared):
    for project, rows in prepared.tasks.items():
        for data in rows:
            assert set(data) == tasks.TASK_KEYS[project]


def test_every_mapping_row_has_task(prepared):
    ids = {d["item_id"] for rows in prepared.tasks.values() for d in rows}
    assert ids == {r.item_id for r in prepared.mapping}


def test_stratified_pick_is_seeded():
    import random
    ids = [f"{p}-{i:03d}" for p in ("VEN", "COB", "ENT") for i in range(1, 6)]
    a = tasks.stratified_pick(ids, 6, random.Random(1))
    assert a == tasks.stratified_pick(ids, 6, random.Random(1))
    assert {s.split("-")[0] for s in a} == {"VEN", "COB", "ENT"}
