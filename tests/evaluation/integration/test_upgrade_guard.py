import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "evaluation/scripts/version_guard.sh"


def run(tmp_path, want, have=None, allow=False):
    marker = tmp_path / "ls-version"
    if have:
        marker.write_text(have + "\n")
    env = dict(os.environ, LS_VERSION=want, EVAL_VERSION_MARKER=str(marker))
    if allow:
        env["EVAL_ALLOW_UPGRADE"] = "1"
    return subprocess.run([str(SCRIPT)], env=env, capture_output=True, text=True), marker


def test_first_run_writes_marker(tmp_path):
    r, marker = run(tmp_path, "1.23.2")
    assert r.returncode == 0 and marker.read_text().strip() == "1.23.2"


def test_same_version_ok(tmp_path):
    assert run(tmp_path, "1.23.2", have="1.23.2")[0].returncode == 0


def test_different_version_refused_with_explanation(tmp_path):
    r, marker = run(tmp_path, "1.24.0", have="1.23.2")
    assert r.returncode != 0 and "1.23.2" in r.stderr and "EVAL_ALLOW_UPGRADE=1" in r.stderr
    assert marker.read_text().strip() == "1.23.2"


def test_upgrade_allowed_when_explicit(tmp_path):
    r, marker = run(tmp_path, "1.24.0", have="1.23.2", allow=True)
    assert r.returncode == 0 and marker.read_text().strip() == "1.24.0"
