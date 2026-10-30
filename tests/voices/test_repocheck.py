import shutil
import subprocess
from pathlib import Path

import pytest

from tts_bench.voices.repocheck import check_repo

ROOT = Path(__file__).resolve().parents[2]
FILES = ["cloned_voices/library.json", "cloned_voices/x/a.wav", "a.wav", "a.safetensors", "a.onnx"]


def git(repo, *a):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init")
    shutil.copy(ROOT / ".gitignore", tmp_path / ".gitignore")
    for f in FILES:
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f).write_bytes(b"x")
    return tmp_path


def test_ignored_and_clean(repo):
    for f in FILES:
        assert subprocess.run(["git", "check-ignore", f], cwd=repo, capture_output=True).returncode == 0, f
    git(repo, "add", "-A"); git(repo, "commit", "-m", "init")
    assert check_repo(repo) == []


def test_forced_add_flagged(repo):
    git(repo, "add", "-f", "a.onnx")
    assert check_repo(repo) == ["a.onnx"]


def test_history_flagged_after_delete(repo):
    git(repo, "add", "-f", "a.safetensors"); git(repo, "commit", "-m", "oops")
    git(repo, "rm", "-f", "a.safetensors"); git(repo, "commit", "-m", "del")
    assert check_repo(repo) == ["a.safetensors"]
