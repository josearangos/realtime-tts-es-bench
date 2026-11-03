import sys

import pytest

from tests.backend.conftest import request_body, ws_collect

FIELDS = ["name", "engine_version", "model_id", "license_code", "license_model", "license_flags", "language",
          "spanish_variant", "supports_cloning", "voice_kind", "streaming", "input_limit_chars", "voices",
          "availability", "state", "queue_depth"]


def _by_name(client):
    return {e["name"]: e for e in client.get("/v1/engines").json()["engines"]}


def test_listing_has_every_field_for_every_engine(client, backend):
    engines = _by_name(client)
    assert {"fake", "phonon", "pocket_tts", "piper"} <= set(engines)
    for name, e in engines.items():
        for f in FIELDS:
            assert f in e, (name, f)
        assert e["streaming"]["granularity"] in ("chunk", "sentence", "none")
    assert "non-commercial" in engines["phonon"]["license_flags"]
    assert "copyleft" in engines["piper"]["license_flags"]
    # no worker was started by listing (only --describe probes ran)
    assert all(s.state == "not_started" for s in backend.supervisors.values())


def test_missing_venv_is_unavailable_with_reason(client):
    a = _by_name(client)["phonon"]["availability"]
    assert a["status"] == "unavailable" and a["reason"] == "venv_missing" and a["hint"]


def test_describe_failure_passes_adapter_hint(backend_factory):
    b = backend_factory(describe_fail="weights_missing")
    a = _by_name(b.client)["fake"]["availability"]
    assert a == {"status": "unavailable", "reason": "weights_missing", "hint": a["hint"]} and "Download" in a["hint"]
    b2 = backend_factory(describe_fail="not_installed")
    a = _by_name(b2.client)["fake"]["availability"]
    assert a["reason"] == "not_installed" and "pip install" in a["hint"]


def test_load_failure_flips_cached_availability(backend_factory):
    b = backend_factory()
    assert _by_name(b.client)["fake"]["availability"]["status"] == "available"
    b.config.worker_env["TTS_FAKE_DESCRIBE_FAIL"] = "weights_missing"
    r = b.client.post("/v1/synthesize", json=request_body())
    assert r.status_code == 409 and r.json()["error"] == "engine_unavailable"
    assert r.json()["reason"] == "weights_missing"
    a = _by_name(b.client)["fake"]["availability"]
    assert a["status"] == "unavailable" and a["reason"] == "weights_missing"


def test_one_engine_and_unknown(client):
    assert client.get("/v1/engines/fake").json()["name"] == "fake"
    r = client.get("/v1/engines/nope")
    assert r.status_code == 404 and r.json()["error"] == "unknown_engine" and "fake" in r.json()["available"]


def test_refresh_after_venv_appears(client, backend):
    assert _by_name(client)["phonon"]["availability"]["reason"] == "venv_missing"
    backend.config.python_overrides["phonon"] = sys.executable  # the venv "appears"
    stale = _by_name(client)["phonon"]["availability"]["reason"]
    assert stale == "venv_missing"  # cached until refresh
    engines = {e["name"]: e for e in client.post("/v1/engines/refresh").json()["engines"]}
    assert engines["phonon"]["availability"]["reason"] in ("not_installed", "weights_missing") or \
        engines["phonon"]["availability"]["status"] == "available"


def test_engine_without_voices_has_note_and_rejects_requests(client):
    e = _by_name(client)["pocket_tts"]
    assert e["voices"] == [] and e["note"]
