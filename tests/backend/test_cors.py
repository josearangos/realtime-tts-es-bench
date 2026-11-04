"""CORS allowlist and WebSocket Origin check (feature 008)."""

import pytest
from starlette.websockets import WebSocketDisconnect

from tests.backend.conftest import request_body, ws_collect
from tts_bench.backend.config import BackendConfig

ALLOWED = "http://127.0.0.1:5173"


def test_allowed_origin_gets_cors_header(client):
    r = client.get("/v1/engines", headers={"Origin": ALLOWED})
    assert r.headers["access-control-allow-origin"] == ALLOWED
    assert "access-control-allow-credentials" not in r.headers


def test_disallowed_origin_gets_no_header(client):
    r = client.get("/v1/engines", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_websocket_bad_origin_is_rejected(client):
    with client.websocket_connect("/v1/ws/synthesize", headers={"Origin": "http://evil.example"}) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert ws.receive()["type"] == "websocket.close"


def test_websocket_allowed_origin_works(client):
    with client.websocket_connect("/v1/ws/synthesize", headers={"Origin": ALLOWED}) as ws:
        ws.send_json(request_body())
        assert ws.receive_json()["type"] == "start"


def test_websocket_without_origin_still_works(client):
    start, _chunks, audio, last, _ = ws_collect(client, request_body())
    assert start and audio and last["type"] == "summary"


def test_empty_list_disables_browser_access(backend_factory):
    b = backend_factory(first_chunk_s=0.01, chunk_interval_s=0.01, audio_s=0.1, chunks=2)
    b.config.cors_origins = []
    # config is read when the app is created, so rebuild with an empty list
    from fastapi.testclient import TestClient

    from tts_bench.backend.app import create_app

    app = create_app(b.config, library=b.library)
    with TestClient(app) as c:
        r = c.get("/v1/engines", headers={"Origin": ALLOWED})
        assert "access-control-allow-origin" not in r.headers
        with c.websocket_connect("/v1/ws/synthesize", headers={"Origin": ALLOWED}) as ws:
            assert ws.receive_json()["type"] == "error"


def test_config_defaults_env_and_no_wildcard(monkeypatch, tmp_path):
    monkeypatch.delenv("TTS_BACKEND_CORS_ORIGINS", raising=False)
    cfg = BackendConfig.load(tmp_path / "none.toml")
    assert cfg.cors_origins == ["http://127.0.0.1:5173", "http://localhost:5173"]
    monkeypatch.setenv("TTS_BACKEND_CORS_ORIGINS", "http://a.test:1, * ,http://b.test:2/")
    assert BackendConfig.load(tmp_path / "none.toml").cors_origins == ["http://a.test:1", "http://b.test:2"]
    monkeypatch.setenv("TTS_BACKEND_CORS_ORIGINS", "")
    assert BackendConfig.load(tmp_path / "none.toml").cors_origins == []
    toml = tmp_path / "b.toml"
    toml.write_text('cors_origins = ["http://c.test:3"]\n')
    monkeypatch.delenv("TTS_BACKEND_CORS_ORIGINS")
    assert BackendConfig.load(toml).cors_origins == ["http://c.test:3"]
