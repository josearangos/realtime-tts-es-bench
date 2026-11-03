"""Read and write manifest, embeddings and results files (JSON, UTF-8, sorted keys).

No absolute path, host name or user name is stored. Shared helpers come from the
intelligibility package rather than being copied.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..intelligibility.files import (  # noqa: F401  (re-exported)
    FileFormatError, canonical_json, environment_block, sanitize_path, sha256_file, sha256_json, utc_stamp,
)
from ..metrics.environment import _clean
from .model import SCHEMA_VERSION, EmbeddingsFile, Manifest, ResultsFile

MANIFEST_NAME = "manifest.json"
EMBEDDINGS_NAME = "embeddings.json"


def sanitized_command(argv: list[str]) -> str:
    """The speaker CLI invocation with paths cleaned (the intelligibility helper hardcodes its own prefix)."""
    out = []
    for a in argv:
        if a.startswith("--") and "=" in a:
            k, v = a.split("=", 1)
            out.append(f"{k}={_clean(v)}")
        else:
            out.append(_clean(a))
    return " ".join(["python -m tts_bench.speaker", *out])


def _write(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data), encoding="utf-8")
    return path


def _read(path: Path, what: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileFormatError(f"{what} file not found: {sanitize_path(path)}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FileFormatError(f"{what} file is not valid JSON: {sanitize_path(path)} ({exc})") from exc
    if not isinstance(data, dict) or "schema_version" not in data:
        raise FileFormatError(f"{what} file has no schema_version: {sanitize_path(path)}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise FileFormatError(
            f"{what} file has unknown schema_version {data['schema_version']!r}; "
            f"this version reads {SCHEMA_VERSION}")
    return data


def _load(cls, data: dict, what: str, path):
    try:
        return cls.from_dict(data)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise FileFormatError(f"{what} file is malformed: {sanitize_path(path)} ({exc!r})") from exc


def _file_in(path: str | Path, name: str) -> Path:
    p = Path(path)
    return p / name if p.is_dir() else p


def write_manifest(manifest: Manifest, directory: str | Path) -> Path:
    return _write(Path(directory) / MANIFEST_NAME, manifest.to_dict())


def read_manifest(path: str | Path) -> Manifest:
    p = _file_in(path, MANIFEST_NAME)
    return _load(Manifest, _read(p, "manifest"), "manifest", p)


def write_embeddings(e: EmbeddingsFile, path: str | Path) -> Path:
    return _write(_file_in(path, EMBEDDINGS_NAME), e.to_dict())


def read_embeddings(path: str | Path) -> EmbeddingsFile:
    p = _file_in(path, EMBEDDINGS_NAME)
    return _load(EmbeddingsFile, _read(p, "embeddings"), "embeddings", p)


def write_results(r: ResultsFile, path: str | Path) -> Path:
    return _write(Path(path), r.to_dict())


def read_results(path: str | Path) -> ResultsFile:
    p = Path(path)
    return _load(ResultsFile, _read(p, "results"), "results", p)
