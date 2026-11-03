import pytest

from tests.backend.conftest import request_body, ws_collect


def test_known_figures_within_5_percent(backend_factory):
    b = backend_factory(first_chunk_s=0.2, chunk_interval_s=0.05, audio_s=1.0, chunks=4)
    start, chunks, audio, last, _ = ws_collect(b.client, request_body())
    assert last["type"] == "summary"
    assert last["ttfa_ms"] == pytest.approx(200, rel=0.05)
    assert last["generation_ms"] == pytest.approx(350, rel=0.08)  # sleep overshoot on a loaded host
    assert last["audio_seconds"] == 1.0
    assert last["rtf"] == pytest.approx(last["generation_ms"] / 1000 / 1.0)
    assert last["chunks"] == 4 and last["kind"] == "interactive" and last["granularity"] == "chunk"
    assert start["engine_version"] == "fake-1" and start["model_id"] == "fake"
    assert start["spanish_variant"]
    r = b.client.post("/v1/synthesize", json=request_body())
    import json

    header = json.loads(r.headers["x-tts-summary"])
    assert set(header) >= {"ttfa_ms", "generation_ms", "audio_seconds", "rtf", "chunks", "queue_wait_ms", "kind"}


def test_no_streaming_has_no_ttfa_number(backend_factory):
    b = backend_factory(granularity="none", first_chunk_s=0.05)
    _, _, _, last, _ = ws_collect(b.client, request_body())
    assert last["ttfa_ms"] == "not available"
    assert last["granularity"] == "none"


def test_zero_audio_is_empty_audio_not_rtf(backend_factory):
    b = backend_factory(audio_s=0.0, chunks=1)
    _, _, _, last, _ = ws_collect(b.client, request_body())
    assert last["type"] == "error" and last["error"] == "empty_audio"
    assert "rtf" not in last
