"""Load and validate evaluation/batch.toml."""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(ValueError):
    """Invalid batch configuration (CLI exit code 2)."""


@dataclass(frozen=True)
class BatchConfig:
    seed: int
    sentences_per_condition: int
    repeat_rate: float
    attention_rate: float
    loudness_rms_dbfs: float = -23.0
    peak_limit_dbfs: float = -1.0
    conditions: tuple[tuple[str, str], ...] = ()
    cmos_pairs: object = "all"
    repeat_within_1_min: float = 0.7
    max_failed_checks: int = 1
    sha256: str = field(default="", compare=False)


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[3] / "evaluation" / "batch.toml"


def load_config(path: str | Path | None = None) -> BatchConfig:
    path = Path(path) if path is not None else default_config_path()
    try:
        raw = path.read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML: {exc}") from None

    def need(key, kind):
        if key not in data:
            raise ConfigError(f"{path}: missing '{key}'")
        v = data[key]
        if isinstance(v, bool) or not isinstance(v, kind):
            raise ConfigError(f"{path}: '{key}' has the wrong type")
        return v

    seed = need("seed", int)
    n = need("sentences_per_condition", int)
    if n < 1:
        raise ConfigError("sentences_per_condition must be >= 1")
    repeat = float(need("repeat_rate", (int, float)))
    if not 0 <= repeat <= 0.3:
        raise ConfigError("repeat_rate must be between 0 and 0.3")
    attention = float(need("attention_rate", (int, float)))
    if not 0 <= attention <= 0.2:
        raise ConfigError("attention_rate must be between 0 and 0.2")
    rms = float(data.get("loudness_rms_dbfs", -23))
    peak = float(data.get("peak_limit_dbfs", -1))
    if rms >= 0 or peak > 0 or rms > peak:
        raise ConfigError("loudness_rms_dbfs must be negative and not above peak_limit_dbfs")
    conds = []
    for c in data.get("conditions", []):
        if not isinstance(c, dict) or "engine" not in c or "voice" not in c:
            raise ConfigError("each condition needs 'engine' and 'voice'")
        conds.append((str(c["engine"]), str(c["voice"])))
    pairs = data.get("cmos_pairs", "all")
    if pairs != "all" and not (isinstance(pairs, list) and all(isinstance(p, list) and len(p) == 2 for p in pairs)):
        raise ConfigError("cmos_pairs must be 'all' or a list of [condA, condB]")
    q = data.get("quality_thresholds", {})
    return BatchConfig(
        seed=seed, sentences_per_condition=n, repeat_rate=repeat, attention_rate=attention,
        loudness_rms_dbfs=rms, peak_limit_dbfs=peak, conditions=tuple(conds), cmos_pairs=pairs,
        repeat_within_1_min=float(q.get("repeat_within_1_min", 0.7)),
        max_failed_checks=int(q.get("max_failed_checks", 1)),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
