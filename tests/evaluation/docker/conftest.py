"""Shared helpers for the opt-in real-stack tests (pytest -m docker). Skipped when no Docker daemon runs."""
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TOKEN = "change-me-token"


def docker_ready() -> bool:
    return bool(shutil.which("docker")) and subprocess.run(["docker", "info"], capture_output=True).returncode == 0


@pytest.fixture(scope="session")
def env_file():
    if not docker_ready():
        pytest.skip("Docker daemon not available")
    path = ROOT / "evaluation" / ".env"
    created = not path.exists()
    if created:
        shutil.copy(ROOT / "evaluation" / ".env.example", path)
    yield path
    if created:
        path.unlink()


def make(*args, env=None, stdin=None):
    return subprocess.run(["make", *args], cwd=ROOT, env=dict(os.environ, **(env or {})), input=stdin,
                          capture_output=True, text=True)


def api(path, method="GET", body=None, port=8080):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"})
    raw = urllib.request.urlopen(req, timeout=30).read()
    return json.loads(raw) if raw.strip() else None
