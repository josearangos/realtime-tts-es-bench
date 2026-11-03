import json
import threading
import time

import pytest

from tests.backend.conftest import request_body, ws_collect


def _post(client, out, key, body, delay=0.0):
    time.sleep(delay)
    out[key] = client.post("/v1/synthesize", json=body)


def _log_lines(b):
    return [json.loads(x) for x in b.log_path.read_text(encoding="utf-8").splitlines()]


def test_serialized_with_queue_wait_and_busy(backend_factory):
    b = backend_factory(first_chunk_s=0.2, chunk_interval_s=0.2, audio_s=0.4, chunks=4)  # ~0.8 s each
    b.client.post("/v1/engines/fake/load")
    out = {}
    threads = [threading.Thread(target=_post, args=(b.client, out, i, request_body(request_id=f"c{i}"), i * 0.1))
               for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert out[3].status_code == 429
    body = out[3].json()
    assert body["error"] == "engine_busy" and body["queue_depth"] == 2
    s0 = json.loads(out[0].headers["x-tts-summary"])
    s1 = json.loads(out[1].headers["x-tts-summary"])
    assert s1["queue_wait_ms"] == pytest.approx(s0["generation_ms"], rel=0.25)
    assert s1["ttfa_ms"] < 400  # not inflated by the wait
    statuses = sorted(x["status"] for x in _log_lines(b))
    assert statuses.count("ok") == 3 and statuses.count("rejected") == 1


def test_different_engines_run_concurrently(backend_factory):
    b = backend_factory(first_chunk_s=0.1, chunk_interval_s=0.2, audio_s=0.4, chunks=4)
    b.client.post("/v1/engines/fake/load")
    b.client.post("/v1/engines/fake2/load")
    starts = {}

    def run(engine, voice, delay):
        time.sleep(delay)
        starts[engine] = ws_collect(b.client, request_body(engine=engine, voice=voice))

    ts = [threading.Thread(target=run, args=("fake", "voz-fake", 0)),
          threading.Thread(target=run, args=("fake2", "voz-fake2", 0.15))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert all(v[3]["type"] == "summary" for v in starts.values())
    assert starts["fake2"][0]["concurrent_engines"] == 1
    assert starts["fake2"][0]["queue_wait_ms"] < 50  # different engine: no waiting
    assert max(x["concurrent_engines"] for x in _log_lines(b)) == 1
