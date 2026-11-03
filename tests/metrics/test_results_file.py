import json
import os
from pathlib import Path

import pytest

from tts_bench.metrics.__main__ import main
from tts_bench.metrics.results import ResultsFileError, read_results, write_results

ENV_KEYS = {
    "hardware": ["cpu_model", "physical_cores", "logical_cores", "ram_gib", "gpu_model", "os_name", "os_release",
                 "hardware_key"],
    "software": ["python", "libraries", "tts_bench_version", "git_commit"],
    "engine": ["name", "engine_version", "model_id", "spanish_variant", "streaming_granularity", "locality", "voice"],
    "config": ["mode", "repetitions", "warmup", "subset", "limit", "thread_settings", "load_threshold"],
    "corpus": ["corpus_version", "corpus_hash"],
}


@pytest.fixture
def run_file(tmp_path):
    out = tmp_path / "out"
    assert main(["run", "fake", "--mode", "cold", "--limit", "3", "--repetitions", "2", "--out", str(out)]) == 0
    (path,) = out.glob("fake-cold-*.json")
    return path


def test_environment_keys_present(run_file):
    env = json.loads(run_file.read_text())["environment"]
    for group, keys in ENV_KEYS.items():
        for k in keys:
            assert k in env[group], f"{group}.{k} missing"
    assert "command" in env and "started_utc" in env


def test_command_string_and_no_private_data(run_file, tmp_path):
    text = run_file.read_text()
    env = json.loads(text)["environment"]
    assert env["command"].startswith("python -m tts_bench.metrics run fake")
    assert "<abs-path>" in env["command"]  # the absolute --out under tmp_path
    assert str(tmp_path) not in text
    assert str(Path.home()) not in text
    import getpass, socket
    assert getpass.getuser() not in text.replace("tts_bench", "")
    assert socket.gethostname() not in text


def test_round_trip_and_schema_refusal(run_file, tmp_path):
    res = read_results(run_file)
    again = write_results(res, tmp_path / "again")
    assert read_results(again).to_dict() == res.to_dict()
    bad = tmp_path / "bad.json"
    d = res.to_dict()
    d["schema_version"] = 99
    bad.write_text(json.dumps(d))
    with pytest.raises(ResultsFileError, match="schema_version"):
        read_results(bad)


def test_resources_recorded(run_file):
    r = json.loads(run_file.read_text())["resources"]
    assert r["peak_ram_mib_final"] > 0 and r["ram_method"]
    assert r["cpu_percent_of_one_core"] is not None and r["logical_cores"]
    assert r["peak_vram_mib"] == "not available" or r["peak_vram_mib"] >= 0
    assert "warning" in r["background_load"]
