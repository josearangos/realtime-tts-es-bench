"""Read and write manifest, transcripts and results files (JSON, UTF-8, sorted keys).

No absolute path, host name or user name is stored: paths are relative to the
repository root or `<abs-path>`.
"""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from ..metrics.environment import REPO_ROOT, _clean, _version, git_commit
from .model import SCHEMA_VERSION, Manifest, ResultsFile, Transcripts

MANIFEST_NAME = "manifest.json"


class FileFormatError(Exception):
    """Missing, malformed or unsupported-version file."""


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def sha256_json(data) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sanitize_path(path: str | Path) -> str:
    return _clean(str(path))


def sanitized_command(sub: str, argv: list[str]) -> str:
    out = []
    for a in argv:
        if a.startswith("--") and "=" in a:
            k, v = a.split("=", 1)
            out.append(f"{k}={_clean(v)}")
        else:
            out.append(_clean(a))
    return " ".join(["python -m tts_bench.intelligibility", *out])


def environment_block() -> dict:
    """Python, OS name and release, package version, git commit. No host or user name."""
    return {
        "python": platform.python_version(),
        "os_name": platform.system() or None,
        "os_release": platform.release() or None,
        "tts_bench_version": _version("tts-bench"),
        "git_commit": git_commit(),
        "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _write(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data), encoding="utf-8")
    return path


def _read(path: str | Path, what: str) -> dict:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileFormatError(f"{what} file not found: {sanitize_path(p)}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FileFormatError(f"{what} file is not valid JSON: {sanitize_path(p)} ({exc})") from exc
    if not isinstance(data, dict) or "schema_version" not in data:
        raise FileFormatError(f"{what} file has no schema_version: {sanitize_path(p)}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise FileFormatError(
            f"{what} file has unknown schema_version {data['schema_version']!r}; "
            f"this version reads {SCHEMA_VERSION}"
        )
    return data


def _load(cls, data: dict, what: str, path):
    try:
        return cls.from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise FileFormatError(f"{what} file is malformed: {sanitize_path(path)} ({exc!r})") from exc


def write_manifest(manifest: Manifest, directory: str | Path) -> Path:
    return _write(Path(directory) / MANIFEST_NAME, manifest.to_dict())


def read_manifest(path: str | Path) -> Manifest:
    p = Path(path)
    if p.is_dir():
        p = p / MANIFEST_NAME
    return _load(Manifest, _read(p, "manifest"), "manifest", p)


def write_transcripts(t: Transcripts, path: str | Path) -> Path:
    return _write(Path(path), t.to_dict())


def read_transcripts(path: str | Path) -> Transcripts:
    return _load(Transcripts, _read(path, "transcripts"), "transcripts", path)


def write_results(r: ResultsFile, path: str | Path) -> Path:
    return _write(Path(path), r.to_dict())


def read_results(path: str | Path) -> ResultsFile:
    return _load(ResultsFile, _read(path, "results"), "results", path)
