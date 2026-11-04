import pytest

from tts_bench.evaluation import labelconfig, provision, scales
from tts_bench.evaluation.batch import ScaleMismatch
from tts_bench.evaluation.lsclient import LSClient, LSUnreachable

STORAGE = "/label-studio/files/served"


def client(ls):
    return LSClient(ls.url, ls.token, retries=1, backoff=0)


def test_first_run_creates_then_second_creates_nothing(prepared, fake_ls):
    c = client(fake_ls)
    r1 = provision.provision(c, prepared.out, STORAGE)
    assert len(fake_ls.state.projects) == 3
    for key in ("mos", "cmos", "sim"):
        assert r1[key]["created"] == len(prepared.tasks[key]) and r1[key]["skipped"] == 0
    before = {p["title"]: len(fake_ls.state.tasks[p["id"]]) for p in fake_ls.state.projects}
    calls = fake_ls.state.import_calls
    r2 = provision.provision(c, prepared.out, STORAGE)
    assert all(v["created"] == 0 for v in r2.values())
    assert fake_ls.state.import_calls == calls  # nothing even sent (SC-005)
    assert before == {p["title"]: len(fake_ls.state.tasks[p["id"]]) for p in fake_ls.state.projects}
    assert all(len(fake_ls.state.storages[p["id"]]) == 1 for p in fake_ls.state.projects)


def test_projects_use_spanish_titles_and_random_sampling(prepared, fake_ls):
    provision.provision(client(fake_ls), prepared.out, STORAGE)
    assert {p["title"] for p in fake_ls.state.projects} == set(labelconfig.TITLES.values())
    assert all(p["sampling"] == "Uniform sampling" for p in fake_ls.state.projects)


def test_changed_anchor_blocks_with_scale_mismatch(prepared, fake_ls, monkeypatch):
    provision.provision(client(fake_ls), prepared.out, STORAGE)
    monkeypatch.setitem(scales.SIM["anchors"], 5, "Otra cosa")
    with pytest.raises(ScaleMismatch):
        provision.provision(client(fake_ls), prepared.out, STORAGE)


def test_cli_exit_codes(prepared, fake_ls, monkeypatch):
    from tts_bench.evaluation.__main__ import main
    base = ["--url", fake_ls.url, "--token", fake_ls.token, "--output", str(prepared.out)]
    assert main([*base, "provision"]) == 0
    monkeypatch.setitem(scales.SIM["anchors"], 5, "Otra cosa")
    assert main([*base, "provision"]) == 4
    assert main(["--url", fake_ls.url, "--token", "", "--output", str(prepared.out), "provision"]) == 2


def test_unreachable_server_times_out(prepared):
    c = LSClient("http://127.0.0.1:1", "x", retries=1, backoff=0)
    with pytest.raises(LSUnreachable):
        provision.provision(c, prepared.out, STORAGE, wait_timeout=0.3)


def test_prepare_missing_batch_is_usage_error(tmp_path, fake_ls):
    with pytest.raises(provision.UsageError):
        provision.provision(client(fake_ls), tmp_path / "none", STORAGE)


def test_inspect_shows_only_visible_data(prepared, fake_ls):
    provision.provision(client(fake_ls), prepared.out, STORAGE)
    shown = provision.inspect(client(fake_ls))
    assert shown == prepared.tasks


def test_cli_prepare_then_provision_end_to_end(tmp_path, fake_ls, monkeypatch, capsys):
    from tts_bench.evaluation import fakes
    from tts_bench.evaluation.__main__ import main

    data = fakes.make_fake_dataset(tmp_path / "data")
    (tmp_path / "evaluation").mkdir()
    (tmp_path / "evaluation" / "batch.toml").write_text(
        'seed = 5\nsentences_per_condition = 4\nrepeat_rate = 0.1\nattention_rate = 0.05\n')
    monkeypatch.chdir(tmp_path)
    out = str(tmp_path / "out")
    base = ["--url", fake_ls.url, "--token", fake_ls.token, "--output", out]
    assert main([*base, "prepare", "--corpus", str(data["corpus"]), "--output-root", str(data["output"]),
                 "--voices-dir", str(data["voices_dir"])]) == 0
    assert main([*base, "prepare", "--corpus", str(data["corpus"]), "--output-root", str(data["output"]),
                 "--voices-dir", str(data["voices_dir"])]) == 0  # frozen batch reused
    assert main([*base, "provision"]) == 0
    assert len(fake_ls.state.projects) == 3
    assert main([*base, "prepare", "--corpus", str(data["corpus"]), "--output-root", str(tmp_path / "empty"),
                 "--new-batch"]) == 2  # nothing to prepare is a usage error, not a crash


def test_list_tasks_on_empty_project_and_pagination(fake_ls):
    c = client(fake_ls)
    pid = c.create_project("vacío", "<View/>", "", "Uniform sampling")["id"]
    assert c.list_tasks(pid) == []
    c.import_tasks(pid, [{"item_id": f"{i:012x}"} for i in range(250)])
    assert len(c.list_tasks(pid)) == 250
