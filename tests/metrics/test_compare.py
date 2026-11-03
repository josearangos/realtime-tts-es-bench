import copy
import json

import pytest

from tts_bench.metrics.__main__ import main
from tts_bench.metrics.compare import CompareRefusedError, compare_results

DIST = {"p50": 1.0, "p95": 2.0, "mean": 1.2, "n": 10, "p95_low_sample": True}


def make(tmp_path, name, *, mode="warm", engine="fake", **env_over):
    env = {
        "hardware": {"cpu_model": "M1", "physical_cores": 8, "logical_cores": 8, "ram_gib": 16.0,
                     "gpu_model": None, "os_name": "Darwin", "os_release": "25.2.0", "hardware_key": "k"},
        "software": {"python": "3.11", "libraries": {"numpy": "2.0"}, "tts_bench_version": "0.1.0", "git_commit": "abc"},
        "engine": {"name": engine, "engine_version": "1", "model_id": "m", "spanish_variant": "es",
                   "streaming_granularity": "chunk", "locality": "local",
                   "voice": {"name": "v", "kind": "fixed_voice", "checksum": None}},
        "config": {"mode": mode, "repetitions": 5, "warmup": 3, "subset": "main", "limit": None,
                   "thread_settings": {}, "load_threshold": 0.25},
        "corpus": {"corpus_version": "1", "corpus_hash": "h"},
        "command": "python -m tts_bench.metrics run", "started_utc": "2026-01-01T00:00:00Z",
    }
    for dotted, v in env_over.items():
        a, b = dotted.split("__")
        env[a][b] = v
    doc = {
        "schema_version": 1, "environment": env,
        "summary": {"n_ok": 10, "n_failed": 0, "n_invalid": 0, "n_total": 10, "reliable": True,
                    "ttfa_ms": DIST, "rtf": DIST, "generation_ms": DIST,
                    "throughput_audio_s_per_s": {"median": 3.0, "per_repetition": [3.0]}, "load_time_ms": 100.0},
        "resources": {"peak_ram_mib_final": 500.0, "cpu_percent_of_one_core": 90.0, "peak_vram_mib": "not available"},
        "measurements": [],
    }
    p = tmp_path / name
    p.write_text(json.dumps(copy.deepcopy(doc)))
    return p


def test_identical_hardware_merges(tmp_path):
    out = compare_results([make(tmp_path, "a.json", engine="a"), make(tmp_path, "b.json", engine="b")])
    assert "## warm" in out and "| a |" in out and "| b |" in out


@pytest.mark.parametrize("field,value", [
    ("hardware__cpu_model", "Other"), ("hardware__logical_cores", 4), ("hardware__ram_gib", 32.0),
    ("hardware__gpu_model", "RTX"), ("hardware__os_name", "Linux"), ("hardware__os_release", "24.0.0"),
])
def test_hardware_difference_refused_and_overridable(tmp_path, field, value):
    a, b = make(tmp_path, "a.json"), make(tmp_path, "b.json", **{field: value})
    with pytest.raises(CompareRefusedError, match=field.split("__")[1]):
        compare_results([a, b])
    assert "Warning: mixed hardware" in compare_results([a, b], allow_mixed_hardware=True)


def test_soft_differences_do_not_block(tmp_path):
    a = make(tmp_path, "a.json")
    b = make(tmp_path, "b.json", software__python="3.12", config__thread_settings={"OMP_NUM_THREADS": "2"})
    out = compare_results([a, b])
    assert "software.python" in out and "config.thread_settings" in out


@pytest.mark.parametrize("field,value", [
    ("corpus__corpus_version", "2"), ("corpus__corpus_hash", "x"), ("config__subset", "cloning"),
    ("config__limit", 5), ("engine__locality", "remote"),
])
def test_strict_differences_refused_even_with_override(tmp_path, field, value):
    a, b = make(tmp_path, "a.json"), make(tmp_path, "b.json", **{field: value})
    with pytest.raises(CompareRefusedError):
        compare_results([a, b], allow_mixed_hardware=True)


def test_cold_and_warm_separate_tables(tmp_path):
    out = compare_results([make(tmp_path, "a.json", mode="cold"), make(tmp_path, "b.json", mode="warm")])
    assert out.index("## cold") < out.index("## warm")


def test_cli_exit_3_and_no_output_file(tmp_path):
    a, b = make(tmp_path, "a.json"), make(tmp_path, "b.json", hardware__cpu_model="Other")
    md = tmp_path / "out.md"
    assert main(["compare", str(a), str(b), "--out", str(md)]) == 3
    assert not md.exists()
    assert main(["compare", str(a), str(b), "--allow-mixed-hardware", "--out", str(md)]) == 0
    assert md.exists()
