import json
import time

from tests.backend.conftest import request_body, ws_collect

INTERVAL = 0.1


def _wait_state(sup, state, timeout):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if sup.state == state:
            return time.monotonic() - t0
        time.sleep(0.005)
    return None


def _log(b):
    return [json.loads(x) for x in b.log_path.read_text(encoding="utf-8").splitlines()]


def test_disconnect_cancels_and_next_request_works(backend_factory):
    b = backend_factory(first_chunk_s=0.05, chunk_interval_s=INTERVAL, audio_s=1.0, chunks=10)
    ws_collect(b.client, request_body(), cancel_after=1)
    waited = _wait_state(b.supervisors["fake"], "ready", 3)
    assert waited is not None and waited < 2 * INTERVAL + 0.3
    start, chunks, audio, last, _ = ws_collect(b.client, request_body(), cancel_after=10)
    assert last is None or last["type"] == "summary"
    assert len(audio) == 10 or last is None
    assert any(x["status"] == "cancelled" for x in _log(b))


def test_cancel_message(backend_factory):
    b = backend_factory(first_chunk_s=0.05, chunk_interval_s=INTERVAL, audio_s=1.0, chunks=10)
    types = []
    with b.client.websocket_connect("/v1/ws/synthesize") as ws:
        ws.send_json(request_body())
        while True:
            msg = ws.receive()
            if msg["type"] == "websocket.close":
                break
            if msg.get("bytes") is not None:
                types.append("audio")
                if types.count("audio") == 1:
                    ws.send_json({"cancel": True})
            else:
                types.append(json.loads(msg["text"])["type"])
    assert "summary" not in types
    assert types.count("audio") < 10
    assert _wait_state(b.supervisors["fake"], "ready", 3) is not None
    r = b.client.post("/v1/synthesize", json=request_body())
    assert r.status_code == 200
    assert any(x["status"] == "cancelled" for x in _log(b))


def test_unresponsive_worker_is_killed_after_grace(backend_factory):
    b = backend_factory(first_chunk_s=0.05, chunk_interval_s=0.3, audio_s=1.0, chunks=10,
                        ignore_cancel="1", cancel_grace_s=1.0, load_s=0.1)
    ws_collect(b.client, request_body(), cancel_after=1)
    assert _wait_state(b.supervisors["fake"], "not_started", 6) is not None
    assert "killed" in b.supervisors["fake"].events
    start, _, _, last, _ = ws_collect(b.client, request_body(), cancel_after=2)
    assert start["load_ms"] > 0  # reloaded after the kill
    assert any(x["status"] == "cancelled" for x in _log(b))
