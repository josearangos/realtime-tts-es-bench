import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "evaluation" / "scripts" / "preflight.sh"


def run(env_file, extra_env=None, skip_port=True):
    env = dict(os.environ, EVAL_ENV_FILE=str(env_file))
    if skip_port:
        env["EVAL_SKIP_PORT_CHECK"] = "1"
    env.update(extra_env or {})
    return subprocess.run([str(SCRIPT), "--no-runtime"], capture_output=True, text=True, env=env)


def envfile(tmp_path, **kw):
    vals = {"LS_BIND": "127.0.0.1", "LS_PORT": "8080", "LS_ADMIN_PASSWORD": "change-me", "LS_API_TOKEN": "change-me-token"}
    vals.update(kw)
    p = tmp_path / ".env"
    p.write_text("\n".join(f"{k}={v}" for k, v in vals.items()) + "\n")
    return p


def test_missing_env_file(tmp_path):
    r = run(tmp_path / "absent")
    assert r.returncode != 0 and "cp evaluation/.env.example evaluation/.env" in r.stderr


def test_loopback_with_placeholders_is_accepted(tmp_path):
    assert run(envfile(tmp_path)).returncode == 0


def test_placeholder_refused_when_exposed(tmp_path):
    r = run(envfile(tmp_path, LS_BIND="0.0.0.0"))
    assert r.returncode != 0 and "LS_ADMIN_PASSWORD" in r.stderr


def test_exposed_with_real_secrets_warns(tmp_path):
    r = run(envfile(tmp_path, LS_BIND="0.0.0.0", LS_ADMIN_PASSWORD="s3cret-long", LS_API_TOKEN="tok-123456"))
    assert r.returncode == 0 and "plain HTTP" in r.stderr


def test_busy_port_reported_with_hint(tmp_path):
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    port = s.getsockname()[1]
    try:
        r = run(envfile(tmp_path, LS_PORT=str(port)), skip_port=False)
    finally:
        s.close()
    assert r.returncode != 0 and "LS_PORT" in r.stderr and str(port) in r.stderr
