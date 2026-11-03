import os

from tts_bench.metrics import environment, resources


def test_ram_peak():
    value, method = resources.peak_ram_mib()
    assert value > 0
    assert "MiB" in method and method


def test_cpu_timer():
    with resources.CpuTimer() as t:
        sum(i * i for i in range(200_000))
    assert t.percent_of_one_core is not None and t.percent_of_one_core > 0
    assert os.cpu_count()


def test_vram_not_available(monkeypatch):
    monkeypatch.setattr(resources.shutil, "which", lambda _: None)
    monkeypatch.delitem(resources.sys.modules, "torch", raising=False)
    value, note = resources.peak_vram_mib()
    assert value == "not available" and note


def test_background_load_warning(monkeypatch):
    assert resources.background_load(0.25, 0.1, 0.9)["warning"] is True
    assert resources.background_load(0.25, 0.1, 0.2)["warning"] is False
    monkeypatch.setattr(resources.os, "getloadavg", lambda: (8.0, 0, 0))
    monkeypatch.setattr(resources.os, "cpu_count", lambda: 8)
    assert resources.load_per_core() == 1.0


def test_thread_settings(monkeypatch):
    monkeypatch.setenv("OMP_NUM_THREADS", "4")
    monkeypatch.delenv("MKL_NUM_THREADS", raising=False)
    ts = environment.thread_settings()
    assert ts["OMP_NUM_THREADS"] == "4" and ts["MKL_NUM_THREADS"] is None
    assert "VECLIB_MAXIMUM_THREADS" in ts


def test_hardware_key_fields():
    env = {"hardware": {"cpu_model": "X", "logical_cores": 8, "ram_gib": 15.6, "gpu_model": None,
                        "os_name": "Darwin", "os_release": "25.2.0"}}
    assert environment.hardware_key(env) == "X|8|16|None|Darwin|25"
