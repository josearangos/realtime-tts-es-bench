import json

from tests.backend.conftest import request_body, ws_collect


def test_unknown_engine(client):
    r = client.post("/v1/synthesize", json=request_body(engine="nope"))
    assert r.status_code == 404
    body = r.json()
    assert body["error"] == "unknown_engine"
    assert "fake" in body["available"] and "phonon" not in body["available"]  # unavailable ones are not offered


def test_unknown_voice_and_voice_of_other_engine(client):
    for voice in ("no-existe", "voz-fake2"):
        r = client.post("/v1/synthesize", json=request_body(voice=voice))
        assert r.status_code == 400
        body = r.json()
        assert body["error"] == "unknown_voice"
        assert set(body["available"]) == {"voz-fake", "tono-fijo"}


def test_engine_unavailable_has_reason_and_hint(backend_factory):
    b = backend_factory(describe_fail="weights_missing")
    r = b.client.post("/v1/synthesize", json=request_body())
    assert r.status_code == 409
    body = r.json()
    assert body["error"] == "engine_unavailable"
    assert body["reason"] == "weights_missing" and body["hint"]


def test_synthesis_failed_after_chunks(backend_factory):
    b = backend_factory(fail_after=2, chunks=4)
    start, chunks, audio, last, _ = ws_collect(b.client, request_body())
    assert len(audio) == 2
    assert last["type"] == "error" and last["error"] == "synthesis_failed"
    r = b.client.post("/v1/synthesize", json=request_body())
    assert r.status_code == 500 and r.json()["error"] == "synthesis_failed"


def test_empty_audio(backend_factory):
    b = backend_factory(audio_s=0.0, chunks=1)
    r = b.client.post("/v1/synthesize", json=request_body())
    assert r.status_code == 500
    assert r.json()["error"] == "empty_audio"


def test_no_message_contains_a_path(backend_factory, tmp_path):
    b = backend_factory(fail_after=1)
    r = b.client.post("/v1/synthesize", json=request_body(voice="nada"))
    texts = [r.text, b.client.post("/v1/synthesize", json=request_body()).text]
    for t in texts:
        assert str(tmp_path) not in t and "/Users/" not in t
        json.loads(t)
