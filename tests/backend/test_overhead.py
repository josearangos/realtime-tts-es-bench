"""Gateway forwarding overhead on the fake engine (plan Performance Goal; reported, not a benchmark)."""

import os
import statistics
import time

import pytest

from tests.backend.conftest import request_body


def test_gateway_overhead_p95_under_5ms(backend_factory):
    if os.getloadavg()[0] / (os.cpu_count() or 1) > 0.7:
        pytest.skip("machine is under load; overhead figure would not be meaningful")
    b = backend_factory(first_chunk_s=0.02, chunk_interval_s=0.02, audio_s=0.4, chunks=4)
    deltas = []
    for _ in range(50):
        with b.client.websocket_connect("/v1/ws/synthesize") as ws:
            ws.send_json(request_body())
            t0 = time.perf_counter()
            at_ms = {}
            while True:
                msg = ws.receive()
                if msg.get("bytes") is not None:
                    pass
                elif msg.get("text"):
                    import json

                    data = json.loads(msg["text"])
                    if data["type"] == "chunk":
                        at_ms[data["index"]] = (data["at_ms"], (time.perf_counter() - t0) * 1000)
                    elif data["type"] in ("summary", "error"):
                        break
        # client arrival offsets relative to the first chunk vs worker-reported offsets
        first_w, first_c = at_ms[0]
        for i, (w, c) in at_ms.items():
            if i > 0:
                deltas.append(abs((c - first_c) - (w - first_w)))
    deltas.sort()
    p95 = deltas[int(0.95 * len(deltas)) - 1]
    print(f"gateway overhead: median {statistics.median(deltas):.2f} ms, p95 {p95:.2f} ms")
    assert p95 < 5.0
