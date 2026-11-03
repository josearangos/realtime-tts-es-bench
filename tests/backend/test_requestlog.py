import json

from tests.backend.conftest import TEXT, request_body
from tts_bench.backend.requestlog import RequestLog


def _entries(b):
    return [json.loads(x) for x in b.log_path.read_text(encoding="utf-8").splitlines()]


def test_outcomes_logged_without_text(backend_factory):
    b = backend_factory(max_chars=60)
    b.client.post("/v1/synthesize", json=request_body())
    b.client.post("/v1/synthesize", json=request_body(text="a" * 61))
    b.client.post("/v1/synthesize", json=request_body(voice="nada"))
    entries = _entries(b)
    assert [e["status"] for e in entries] == ["ok", "rejected", "rejected"]
    ok = entries[0]
    for key in ("ts", "request_id", "engine", "voice", "text_chars", "text_sha256", "status",
                "summary", "concurrent_engines", "engine_version", "model_id"):
        assert key in ok
    assert ok["text_chars"] == len(TEXT)
    raw = b.log_path.read_text(encoding="utf-8")
    assert TEXT not in raw and "/Users/" not in raw and "voice-" not in raw


def test_empty_audio_is_invalid(backend_factory):
    b = backend_factory(audio_s=0.0, chunks=1)
    b.client.post("/v1/synthesize", json=request_body())
    assert _entries(b)[0]["status"] == "invalid"


def test_text_only_when_enabled(backend_factory):
    b = backend_factory(log_text=True)
    b.client.post("/v1/synthesize", json=request_body())
    assert _entries(b)[0]["text"] == TEXT


def test_rotation(tmp_path):
    log = RequestLog(tmp_path / "r.jsonl", max_bytes=600, keep=2)
    for i in range(12):
        log.log_request(request_id=str(i), engine="fake", voice="v", text="x", status="ok")
    assert (tmp_path / "r.jsonl.1").exists()
    assert not (tmp_path / "r.jsonl.3").exists()
    assert (tmp_path / "r.jsonl").stat().st_size <= 600
