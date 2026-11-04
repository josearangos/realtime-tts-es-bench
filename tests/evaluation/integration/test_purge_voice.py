import json

from tts_bench.evaluation import provision
from tts_bench.evaluation.blind import read_mapping
from tts_bench.evaluation.lsclient import LSClient


def test_purge_voice_removes_files_tasks_rows(prepared, fake_ls):
    c = LSClient(fake_ls.url, fake_ls.token, retries=1, backoff=0)
    provision.provision(c, prepared.out, "/label-studio/files/served")
    before = read_mapping(prepared.out / "private" / "mapping.jsonl")
    doomed = [r for r in before if "clon1" in (r.voice, (r.a or {}).get("voice"), (r.b or {}).get("voice"))]
    keep = [r for r in before if r not in doomed]
    assert doomed and keep
    rec = provision.purge_voice(c, prepared.out, "clon1")
    after = read_mapping(prepared.out / "private" / "mapping.jsonl")
    assert {r.item_id for r in after} == {r.item_id for r in keep}
    served = {f.name for f in (prepared.out / "served").iterdir()}
    for r in doomed:  # incl. SIM reference clips
        assert not served & set(r.served_files)
    for r in keep:
        assert set(r.served_files) <= served
    ls_ids = {t["data"]["item_id"] for p in fake_ls.state.projects for t in fake_ls.state.tasks[p["id"]]}
    assert ls_ids == {r.item_id for r in keep}
    assert rec["items"] == len(doomed)
    log = (prepared.out / "private" / "purges.jsonl").read_text().splitlines()
    assert json.loads(log[-1])["voice"] == "clon1"
    tasks_json = json.loads((prepared.out / "tasks.json").read_text())
    assert {d["item_id"] for v in tasks_json.values() for d in v} == {r.item_id for r in keep}
