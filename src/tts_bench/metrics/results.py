"""Write and read results files (schema_version 1)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .model import SCHEMA_VERSION, ResultsFile


class ResultsFileError(ValueError):
    pass


def write_results(results: ResultsFile, out_dir: str | Path) -> Path:
    env = results.environment
    mode = env.get("config", {}).get("mode", "steady")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{env['engine']['name']}-{mode}-{stamp}.json"
    n = 1
    while path.exists():
        n += 1
        path = out / f"{env['engine']['name']}-{mode}-{stamp}-{n}.json"
    path.write_text(json.dumps(results.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def read_results(path: str | Path) -> ResultsFile:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResultsFileError(f"{path}: cannot read results file ({exc})") from None
    version = raw.get("schema_version") if isinstance(raw, dict) else None
    if version != SCHEMA_VERSION:
        raise ResultsFileError(f"{path}: unsupported schema_version {version!r}; this tool reads {SCHEMA_VERSION}")
    return ResultsFile.from_dict(raw)
