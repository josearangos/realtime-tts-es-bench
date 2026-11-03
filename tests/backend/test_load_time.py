from tests.backend.conftest import request_body, ws_collect


def test_load_reported_once_and_not_in_latency(backend_factory):
    b = backend_factory(load_s=0.3, first_chunk_s=0.02, chunk_interval_s=0.02)
    start, _, _, last, _ = ws_collect(b.client, request_body())
    assert abs(start["load_ms"] - 300) / 300 < 0.15
    assert last["load_ms"] == start["load_ms"] and last["first_request_after_load"] is True
    assert last["ttfa_ms"] < 150 and last["generation_ms"] < 300
    start2, _, _, last2, _ = ws_collect(b.client, request_body())
    assert "load_ms" not in start2 and "load_ms" not in last2


def test_new_load_after_kill(backend_factory):
    b = backend_factory(load_s=0.1)
    ws_collect(b.client, request_body())
    b.supervisors["fake"]._kill("killed")
    start, _, _, _, _ = ws_collect(b.client, request_body())
    assert start["load_ms"] > 50


def test_explicit_load(backend_factory):
    b = backend_factory(load_s=0.2)
    r = b.client.post("/v1/engines/fake/load")
    assert r.status_code == 200 and r.json()["load_ms"] > 150
    start, _, _, _, _ = ws_collect(b.client, request_body())
    assert "load_ms" not in start
    assert b.client.post("/v1/engines/fake/load").json() == {"load_ms": None, "already_loaded": True}
