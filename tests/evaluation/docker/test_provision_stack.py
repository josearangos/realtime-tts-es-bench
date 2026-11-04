"""make eval-up provisions 3 projects, and a second eval-up changes nothing (opt-in: -m docker)."""
import json

import pytest

from .conftest import api, make

pytestmark = pytest.mark.docker


def counts():
    projects = api("/api/projects")
    projects = projects["results"] if isinstance(projects, dict) else projects
    return {p["title"]: p.get("task_number") for p in projects}


def test_auto_provision_is_idempotent(env_file):
    try:
        assert make("eval-reset", stdin="RESET\n").returncode == 0
        r = make("eval-up")
        assert r.returncode == 0, r.stdout + r.stderr
        first = counts()
        assert len(first) == 3 and all(v for v in first.values() if v is not None)
        assert make("eval-up").returncode == 0
        assert counts() == first
        shown = json.loads(make("eval-inspect").stdout)
        assert set(shown) == {"mos", "cmos", "sim"}
        text = json.dumps(shown).lower()
        assert not any(w in text for w in ("piper", "phonon", "pocket"))
    finally:
        make("eval-down")
