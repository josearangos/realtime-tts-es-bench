import io
import wave

import pytest

from tests.backend.conftest import request_body, ws_collect


def test_streaming_chunks_arrive_before_summary(backend_factory):
    b = backend_factory(first_chunk_s=0.05, chunk_interval_s=0.15, audio_s=0.4, chunks=4)
    start, chunks, audio, last, arrivals = ws_collect(b.client, request_body(request_id="r1"))
    assert last["type"] == "summary"
    assert start["request_id"] == "r1"
    assert len(chunks) == 4 and len(audio) == 4
    assert sum(len(a) for a in audio) == sum(c["samples"] for c in chunks) * 2
    assert start["sample_format"] == "s16le" and start["sample_rate"] == 16000 and start["streaming"] is True
    # SC-001: the first audio frame arrives well before the summary (>= one chunk interval)
    first_audio = arrivals[2]  # start, chunk, audio
    assert arrivals[-1] - first_audio >= 0.15


def test_granularity_none_complete_audio_with_notice(backend_factory):
    b = backend_factory(granularity="none", first_chunk_s=0.02, audio_s=0.3)
    start, chunks, audio, last, _ = ws_collect(b.client, request_body())
    assert len(audio) == 1 and len(chunks) == 1
    assert start["streaming_available"] is False and start["notice"]
    assert start["streaming"] is False
    assert last["type"] == "summary"


def test_post_returns_wav(client):
    r = client.post("/v1/synthesize", json=request_body(request_id="p1"))
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert "x-tts-streaming" not in r.headers
    with wave.open(io.BytesIO(r.content)) as w:
        assert w.getframerate() == 16000 and w.getnframes() == 6400
    assert r.headers["x-tts-request-id"] == "p1"


def test_post_non_streaming_header(backend_factory):
    b = backend_factory(granularity="none", first_chunk_s=0.02)
    r = b.client.post("/v1/synthesize", json=request_body())
    assert r.status_code == 200
    assert r.headers["x-tts-streaming"] == "unavailable"
