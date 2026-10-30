from __future__ import annotations

import subprocess
from pathlib import Path

SUFFIXES = (".wav", ".safetensors", ".onnx", ".pt", ".ckpt")


def _is_voice_material(path: str) -> bool:
    return path.startswith("cloned_voices/") or path.lower().endswith(SUFFIXES)


def _git(repo: Path, *args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def check_repo(repo: str | Path = ".") -> list[str]:
    """Paths of voice material that is tracked or was ever added to history. Changes nothing."""
    repo = Path(repo)
    paths = _git(repo, "ls-files")
    try:
        paths += _git(repo, "log", "--all", "--name-only", "--diff-filter=A", "--pretty=format:")
    except subprocess.CalledProcessError:  # no commits yet
        pass
    return sorted({p for p in paths if _is_voice_material(p)})
