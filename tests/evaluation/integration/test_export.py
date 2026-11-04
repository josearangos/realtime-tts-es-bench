import json
import random

import pytest

from tts_bench.evaluation import export, provision
from tts_bench.evaluation.export import ExportError
from tts_bench.evaluation.lsclient import LSClient

STORAGE = "/label-studio/files/served"


def setup(prepared, fake_ls, users=("a01@eval.invalid", "a02@eval.invalid")):
    c = LSClient(fake_ls.url, fake_ls.token, retries=1, backoff=0)
    provision.provision(c, prepared.out, STORAGE)
    uids = [fake_ls.add_user(e) for e in users]
    rng = random.Random(3)
    for p in fake_ls.state.projects:
        key = p["title"][:3].lower()
        for t in fake_ls.state.tasks[p["id"]]:
            for u in uids:
                if key == "mos":
                    result = [{"from_name": k, "to_name": "audio", "type": "rating", "value": {"rating": rng.randint(1, 5)}}
                              for k in ("naturalidad", "pronunciacion", "prosodia")]
                elif key == "cmo":
                    result = [{"from_name": "cmos", "to_name": "audio_a", "type": "choices",
                               "value": {"choices": [str(rng.randint(-3, 3))]}}]
                else:
                    result = [{"from_name": "sim", "to_name": "audio", "type": "rating", "value": {"rating": rng.randint(1, 5)}}]
                fake_ls.annotate(t["id"], u, result, lead_time=4.5, created_at="2026-11-04T10:00:00Z")
    return c


def test_every_row_traces_and_no_pii(prepared, fake_ls, tmp_path):
    c = setup(prepared, fake_ls)
    rows, records, batch = export.collect(c, prepared.out)
    n_tasks = sum(len(v) for v in prepared.tasks.values())
    assert len(rows) == 2 * n_tasks
    for r in rows:
        assert r["annotator_id"] in ("a01", "a02")
        assert r["sentence_id"] and r["corpus_version"] == "9.9.9" and r["scale_hash"] == batch["scale_hash"]
        if r["project"] == "cmos":
            assert r["engine_a"] and r["voice_a"] and r["engine_b"] and r["voice_b"]
        else:
            assert r["engine"] and r["voice"]
    out = tmp_path / "exp"
    export.write_export(rows, records, batch, prepared.cfg, out, "cmd", "1.23.2")
    blob = "".join(p.read_text() for p in out.iterdir())
    assert "@eval.invalid" not in blob and "/data/local-files" not in blob and ".wav" not in blob


def test_two_exports_byte_identical(prepared, fake_ls, tmp_path):
    c = setup(prepared, fake_ls)
    outs = []
    for n in ("e1", "e2"):
        rows, records, batch = export.collect(c, prepared.out)
        export.write_export(rows, records, batch, prepared.cfg, tmp_path / n, "cmd", "1.23.2")
        outs.append(tmp_path / n)
    for name in ("annotations.jsonl", "annotations.csv", "quality.json", "MANIFEST.json"):
        assert (outs[0] / name).read_bytes() == (outs[1] / name).read_bytes()
    keys = [(r["project"], r["item_id"], r["annotator_id"]) for r in map(json.loads, (outs[0] / "annotations.jsonl").read_text().splitlines())]
    assert keys == sorted(keys)


def test_cmos_ab_resolves_to_mapping(prepared, fake_ls):
    c = setup(prepared, fake_ls)
    rows, _, _ = export.collect(c, prepared.out)
    by_id = {r.item_id: r for r in prepared.mapping}
    for r in rows:
        if r["project"] == "cmos":
            m = by_id[r["item_id"]]
            assert (r["engine_a"], r["voice_a"]) == (m.a["engine"], m.a["voice"])
            assert (r["engine_b"], r["voice_b"]) == (m.b["engine"], m.b["voice"])


def test_non_pseudonymous_user_aborts_naming_id_not_email(prepared, fake_ls):
    c = setup(prepared, fake_ls, users=("jane.doe@example.com",))
    with pytest.raises(ExportError) as e:
        export.collect(c, prepared.out)
    assert "jane.doe" not in str(e.value) and "user id" in str(e.value)


def test_missing_mapping_fields_refuse(prepared, fake_ls):
    c = setup(prepared, fake_ls)
    from tts_bench.evaluation.blind import read_mapping, write_mapping
    path = prepared.out / "private" / "mapping.jsonl"
    rows = read_mapping(path)
    next(r for r in rows if r.project == "mos").corpus_version = None
    write_mapping(path, rows)
    with pytest.raises(ExportError, match="corpus_version"):
        export.collect(c, prepared.out)


def test_annotator_command(fake_ls):
    c = LSClient(fake_ls.url, fake_ls.token, retries=1, backoff=0)
    calls = []
    setter = lambda e, p: calls.append((e, p))  # noqa: E731
    email, pw = provision.create_annotator(c, "a03", setter)
    assert email == "a03@eval.invalid" and len(pw) >= 12 and calls == [(email, pw)]
    with pytest.raises(provision.UsageError, match="reset-password"):
        provision.create_annotator(c, "a03", setter)
    email2, pw2 = provision.create_annotator(c, "a03", setter, reset=True)  # existing user: only a new password
    assert pw2 != pw and calls[-1] == (email2, pw2) and len(fake_ls.state.users) == 1
    with pytest.raises(provision.UsageError):
        provision.create_annotator(c, "Maria", setter)


def test_cli_export_writes_files(prepared, fake_ls, tmp_path, monkeypatch):
    setup(prepared, fake_ls)
    from tts_bench.evaluation.__main__ import main
    out = tmp_path / "cli-out"
    monkeypatch.chdir(tmp_path)
    rc = main(["--url", fake_ls.url, "--token", fake_ls.token, "--output", str(prepared.out), "export", "--out", str(out)])
    assert rc == 0 and (out / "MANIFEST.json").exists()
    manifest = json.loads((out / "MANIFEST.json").read_text())
    assert manifest["rows"] > 0 and "numpy" in manifest["environment"] and manifest["command"].startswith("python -m")
