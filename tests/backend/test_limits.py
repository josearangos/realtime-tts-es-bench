from tests.backend.conftest import request_body, ws_collect


def test_exact_limit_accepted_and_one_more_rejected(backend_factory):
    b = backend_factory(max_chars=40)
    ok = b.client.post("/v1/synthesize", json=request_body(text="a" * 40))
    assert ok.status_code == 200
    r = b.client.post("/v1/synthesize", json=request_body(text="a" * 41))
    assert r.status_code == 400
    body = r.json()
    assert body["error"] == "text_too_long" and body["limit"] == 40 and body["received"] == 41
    start, chunks, audio, last, _ = ws_collect(b.client, request_body(text="a" * 41))
    assert start is None and last["error"] == "text_too_long"


def test_engine_limit_is_lower(backend_factory):
    b = backend_factory(max_chars=500)
    b.config.worker_env["TTS_FAKE_MAX_CHARS"] = "10"
    b.client.post("/v1/engines/refresh")
    r = b.client.post("/v1/synthesize", json=request_body(text="a" * 11))
    assert r.status_code == 400 and r.json()["limit"] == 10


def test_empty_and_whitespace(client):
    for text in ("", "   \n"):
        r = client.post("/v1/synthesize", json=request_body(text=text))
        assert r.status_code == 400 and r.json()["error"] == "text_empty"


def test_text_is_not_truncated_and_limit_in_health(client, backend):
    assert client.get("/v1/health").json()["limits"]["max_chars"] == backend.config.max_chars
    assert client.post("/v1/synthesize", json=request_body(text="a" * 500)).status_code == 200
