"""Real-stack lifecycle (opt-in: pytest -m docker). Needs a running Docker daemon."""
import json
import urllib.request

import pytest

from .conftest import ROOT, api, make

pytestmark = pytest.mark.docker
OFF = {"EVAL_PROVISION": "0"}


@pytest.fixture(scope="module", autouse=True)
def stack(env_file):
    yield
    make("eval-down", env=OFF)


def health():
    with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=5) as r:
        return json.loads(r.read())


def test_up_is_healthy():
    r = make("eval-up", env=OFF)
    assert r.returncode == 0, r.stderr
    assert health()["status"] == "UP"


def test_down_up_keeps_data():
    api("/api/projects", "POST", {"title": "persist-check", "label_config": "<View/>"})
    assert make("eval-down", env=OFF).returncode == 0
    assert make("eval-up", env=OFF).returncode == 0
    assert "persist-check" in json.dumps(api("/api/projects"))


def test_reset_requires_exact_confirmation():
    r = make("eval-reset", stdin="no\n")
    assert "nothing changed" in r.stdout and health()["status"] == "UP"
    r = make("eval-reset", stdin="RESET\n")
    assert r.returncode == 0 and "reset done" in r.stdout
    assert not (ROOT / "output" / "evaluation").exists()


def test_start_works_without_network_after_first_build():
    # the image exists from the first test: eval-up must pick --no-build and need no pull (SC-002, SC-007).
    # Full offline proof: disable the host network and rerun this test by hand.
    r = make("eval-up", env=OFF)
    assert r.returncode == 0 and "offline-safe" in r.stdout
