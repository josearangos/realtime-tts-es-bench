from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = yaml.safe_load((ROOT / "evaluation" / "compose.yaml").read_text())
LS = COMPOSE["services"]["label-studio"]
PROV = COMPOSE["services"]["provisioner"]


def test_loopback_default_bind():
    (port,) = LS["ports"]
    assert port.startswith("${LS_BIND:-127.0.0.1}:${LS_PORT:-8080}:")


def test_named_volume_and_healthcheck():
    assert "ls-data" in COMPOSE["volumes"]
    assert any(v.startswith("ls-data:") for v in LS["volumes"])
    assert "/health" in " ".join(LS["healthcheck"]["test"])


def test_provisioner_waits_for_healthy_and_is_profiled():
    assert PROV["depends_on"]["label-studio"]["condition"] == "service_healthy"
    assert PROV["profiles"] == ["provision"]


def test_audio_mount_read_only_and_private_not_mounted():
    served = [v for v in LS["volumes"] if "served" in v]
    assert len(served) == 1 and served[0].endswith(":ro")
    assert not any("private" in v or v.startswith("../output/evaluation:") for v in LS["volumes"])


def test_hardening_env():
    env = LS["environment"]
    assert env["LABEL_STUDIO_DISABLE_SIGNUP_WITHOUT_LINK"] == "true"
    assert env["LABEL_STUDIO_COLLECT_ANALYTICS"] == "false"
    assert env["LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED"] == "true"


def test_no_secrets_committed():
    text = (ROOT / "evaluation" / ".env.example").read_text()
    values = dict(l.split("=", 1) for l in text.splitlines() if "=" in l and not l.startswith("#"))
    assert values["LS_ADMIN_PASSWORD"] == "change-me" and values["LS_API_TOKEN"] == "change-me-token"
    assert values["LS_BIND"] == "127.0.0.1" and values["LS_VERSION"] == "1.23.2"
    compose_text = (ROOT / "evaluation" / "compose.yaml").read_text()
    assert "change-me" not in compose_text


def test_env_file_is_git_ignored():
    assert "evaluation/.env" in (ROOT / ".gitignore").read_text().splitlines()
