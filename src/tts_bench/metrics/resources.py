"""Resource use without extra dependencies and without a sampling thread."""

from __future__ import annotations

import os
import resource
import shutil
import subprocess
import sys
import time

NOT_AVAILABLE = "not available"
LOAD_LAG_NOTE = "1-minute load average lags behind the run; treat the warning as indicative"


def peak_ram_mib() -> tuple[float, str]:
    """Process lifetime peak resident memory in MiB, with the conversion used."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return raw / (1024 * 1024), "getrusage.ru_maxrss (bytes on darwin, divided by 1024*1024 to MiB)"
    return raw / 1024, "getrusage.ru_maxrss (KiB on linux, divided by 1024 to MiB)"


class CpuTimer:
    """Process CPU time against wall time over the measured phase."""

    def __enter__(self) -> "CpuTimer":
        self._cpu0 = time.process_time()
        self._wall0 = time.perf_counter()
        self.percent_of_one_core: float | None = None
        return self

    def __exit__(self, *exc) -> None:
        wall = time.perf_counter() - self._wall0
        cpu = time.process_time() - self._cpu0
        self.percent_of_one_core = 100.0 * cpu / wall if wall > 0 else None


def peak_vram_mib() -> tuple[float | str, str | None]:
    """(value, note). A number only when measured; otherwise 'not available' and the reason."""
    torch = sys.modules.get("torch")
    try:
        if torch is not None and torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / (1024 * 1024), None
    except Exception:  # pragma: no cover - depends on torch build
        pass
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            out = subprocess.run(
                [smi, "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10, check=True,
            ).stdout.split()
            if out:
                return float(max(float(x) for x in out)), None
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    if sys.platform == "darwin":
        return NOT_AVAILABLE, "no discrete GPU memory tool; unified memory is counted under RAM"
    return NOT_AVAILABLE, "no GPU memory tool found (nvidia-smi absent and torch.cuda unavailable)"


def load_per_core() -> float | None:
    try:
        return os.getloadavg()[0] / (os.cpu_count() or 1)
    except (OSError, AttributeError):  # pragma: no cover - platform dependent
        return None


def background_load(threshold: float, before: float | None, after: float | None) -> dict:
    warning = any(v is not None and v > threshold for v in (before, after))
    return {
        "before": before, "after": after, "per_core_threshold": threshold,
        "warning": warning, "note": LOAD_LAG_NOTE,
    }
