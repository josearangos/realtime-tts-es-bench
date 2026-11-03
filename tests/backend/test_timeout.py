import json

from tests.backend.conftest import request_body


def test_slow_engine_times_out_then_recovers(backend_factory):
    b = backend_factory(first_chunk_s=1.5, request_timeout_s=1.0, cancel_grace_s=1.0)
    r = b.client.post("/v1/synthesize", json=request_body())
    assert r.status_code == 504 and r.json()["error"] == "worker_timeout"
    b.config.worker_env["TTS_FAKE_FIRST_CHUNK_S"] = "0.02"
    b.supervisors["fake"]._kill("restart-for-test")  # the next worker picks up the fast settings
    assert b.client.post("/v1/synthesize", json=request_body()).status_code == 200
    entries = [json.loads(x) for x in b.log_path.read_text(encoding="utf-8").splitlines()]
    assert entries[0]["status"] == "failed"
