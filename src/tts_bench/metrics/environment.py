"""Environment record and hardware key. Never stores hostname, user name or home paths."""

from __future__ import annotations

import importlib.metadata as md
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..corpus import corpus_stamp

REPO_ROOT = Path(__file__).resolve().parents[3]
THREAD_VARS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
ENGINE_PACKAGES = {"phonon": "ptts", "pocket_tts": "pocket-tts", "piper": "piper-tts"}
UNKNOWN = None


def _run(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def cpu_model() -> str | None:
    if sys.platform == "darwin":
        return _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or None


def physical_cores() -> int | None:
    if sys.platform == "darwin":
        v = _run(["sysctl", "-n", "hw.physicalcpu"])
        return int(v) if v and v.isdigit() else None
    try:
        pairs = set()
        phys = core = None
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("physical id"):
                phys = line.split(":")[1].strip()
            elif line.startswith("core id"):
                core = line.split(":")[1].strip()
                pairs.add((phys, core))
        return len(pairs) or None
    except OSError:
        return None


def ram_gib() -> float | None:
    try:
        if sys.platform == "darwin":
            v = _run(["sysctl", "-n", "hw.memsize"])
            return round(int(v) / 2**30, 1) if v else None
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30, 1)
    except (ValueError, OSError):
        return None


def gpu_model() -> str | None:
    smi = _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    if smi:
        return smi.splitlines()[0]
    if sys.platform == "darwin":
        chip = cpu_model()
        return chip if chip and "Apple" in chip else None  # integrated GPU of the SoC
    return None


def _version(pkg: str) -> str | None:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return None


def libraries(engine: str) -> dict:
    names = ["numpy", "torch", ENGINE_PACKAGES.get(engine)]
    return {n: v for n in names if n and (v := _version(n)) is not None}


def thread_settings() -> dict:
    out = {v: os.environ.get(v) for v in THREAD_VARS}
    torch = sys.modules.get("torch")
    out["torch_num_threads"] = torch.get_num_threads() if torch is not None else None
    return out


def git_commit() -> str | None:
    return _run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"])


def hardware_key(env: dict) -> str:
    hw = env["hardware"]
    major = (hw.get("os_release") or "").split(".")[0]
    ram = hw.get("ram_gib")
    return "|".join(
        str(x) for x in (hw.get("cpu_model"), hw.get("logical_cores"), round(ram) if ram else None,
                         hw.get("gpu_model"), hw.get("os_name"), major)
    )


def sanitize_args(argv: list[str]) -> str:
    """Absolute paths become relative to the repository root, or `<abs-path>`."""
    out = []
    for a in argv:
        if a.startswith("--") and "=" in a:
            k, v = a.split("=", 1)
            out.append(f"{k}={_clean(v)}")
        else:
            out.append(_clean(a))
    return " ".join(["python -m tts_bench.metrics", *out])


def _clean(arg: str) -> str:
    if not os.path.isabs(arg):
        return arg
    try:
        return str(Path(arg).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return "<abs-path>"


def collect_environment(adapter, voice_info: dict, corpus, config: dict, argv: list[str]) -> dict:
    d = adapter.descriptor
    hw = {
        "cpu_model": cpu_model(),
        "physical_cores": physical_cores(),
        "logical_cores": os.cpu_count(),
        "ram_gib": ram_gib(),
        "gpu_model": gpu_model(),
        "os_name": platform.system() or None,
        "os_release": platform.release() or None,
    }
    env = {
        "hardware": hw,
        "software": {
            "python": platform.python_version(),
            "libraries": libraries(d.name),
            "tts_bench_version": _version("tts-bench"),
            "git_commit": git_commit(),
        },
        "engine": {
            "name": d.name,
            "engine_version": d.engine_version,
            "model_id": d.model_id,
            "spanish_variant": d.spanish_variant,
            "streaming_granularity": d.streaming.granularity,
            "locality": getattr(d, "locality", "local"),
            "voice": voice_info,
        },
        "config": {**config, "thread_settings": thread_settings()},
        "corpus": corpus_stamp(corpus),
        "command": sanitize_args(argv),
        "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "unknown_reasons": {},
    }
    hw["hardware_key"] = hardware_key(env)
    reasons = env["unknown_reasons"]
    for key, why in (("cpu_model", "not detectable on this OS"), ("physical_cores", "not detectable on this OS"),
                     ("ram_gib", "not detectable on this OS"),
                     ("gpu_model", "no GPU detected")):
        if hw[key] is None:
            reasons[f"hardware.{key}"] = why
    if env["software"]["git_commit"] is None:
        reasons["software.git_commit"] = "not a git checkout or git unavailable"
    if env["software"]["tts_bench_version"] is None:
        reasons["software.tts_bench_version"] = "package metadata not installed"
    if voice_info.get("checksum") is None:
        reasons["engine.voice.checksum"] = "voice has no file (catalog or fixed voice)"
    return env
