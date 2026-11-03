"""Fixtures for the backend tests: fake-engine workers, a synthetic voice library, ASGI client.

No weights, no network, no real engine venv, never the real `cloned_voices/`.
"""

from __future__ import annotations

import sys
import time
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from tts_bench.backend.app import create_app  # noqa: E402
from tts_bench.backend.config import BackendConfig  # noqa: E402
from tts_bench.core import registry  # noqa: E402
from tts_bench.voices import ConsentRecord, LocalVoiceLibrary  # noqa: E402

from tests.voices.conftest import make_wav  # noqa: E402

ENV_NAMES = {
    "first_chunk_s": "TTS_FAKE_FIRST_CHUNK_S",
    "chunk_interval_s": "TTS_FAKE_CHUNK_INTERVAL_S",
    "audio_s": "TTS_FAKE_AUDIO_S",
    "chunks": "TTS_FAKE_CHUNKS",
    "granularity": "TTS_FAKE_GRANULARITY",
    "load_s": "TTS_FAKE_LOAD_S",
    "fail_after": "TTS_FAKE_FAIL_AFTER",
    "describe_fail": "TTS_FAKE_DESCRIBE_FAIL",
    "ignore_cancel": "TTS_FAKE_IGNORE_CANCEL",
    "max_chars": "TTS_FAKE_MAX_CHARS",
}

TEXT = "Buenos días, ¿en qué le puedo ayudar hoy?"


def build_library(root, tmp_path):
    lib = LocalVoiceLibrary(root)
    lib.add_consent(ConsentRecord("ana", "2025", ["internal_benchmarking"], ["outbound_sales", "cloning_prompts"]))
    rec = lib.add_recording(make_wav(tmp_path / "ref.wav", 12), "ana", "es-CO", no_music_confirmed=True)
    for name, engine in (("voz-fake", "fake"), ("voz-fake2", "fake2"), ("voz-phonon", "phonon")):
        f = tmp_path / f"{name}.bin"
        f.write_bytes(b"voice-" + name.encode())
        lib.register(
            name, engine, "stored_voice_file", f, recording_id=rec.recording_id,
            segment={"start_s": 0, "length_s": 10}, creation="external: test", accent_label="es-CO",
        )
    tone = tmp_path / "tono.bin"
    tone.write_bytes(b"fixed-tone")
    lib.register_fixed("tono-fijo", "fake", str(tone), accent_label="none (synthetic tone)", creation="test")
    return lib


def make_backend(tmp_path, **env):
    config = BackendConfig(log_path=str(tmp_path / "output" / "backend" / "requests.jsonl"))
    for key in ("queue_waiting", "cancel_grace_s", "request_timeout_s", "max_chars", "log_text"):
        if key in env:
            setattr(config, key, env.pop(key))
    config.python_overrides = {"fake": sys.executable, "fake2": sys.executable}
    config.venvs = {n: str(tmp_path / f"missing-{n}") for n in ("phonon", "pocket_tts", "piper")}
    config.worker_env = {ENV_NAMES[k]: v for k, v in env.items() if v is not None}
    registry.register("fake2", "tts_bench.adapters.fake:FakeAdapter")
    library = build_library(tmp_path / "lib", tmp_path)
    app = create_app(config, library=library)
    return SimpleNamespace(app=app, config=config, library=library, supervisors=app.state.supervisors,
                           log_path=config.log_dir / "requests.jsonl")


class BackendFactory:
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path
        self._clients: list[TestClient] = []

    def __call__(self, **env):
        sub = self.tmp_path / f"b{len(self._clients)}"
        sub.mkdir()
        b = make_backend(sub, **env)
        client = TestClient(b.app)
        client.__enter__()
        self._clients.append(client)
        b.client = client
        return b

    def close(self):
        for c in self._clients:
            c.__exit__(None, None, None)
        registry._REGISTRY.pop("fake2", None)


@pytest.fixture
def backend_factory(tmp_path):
    f = BackendFactory(tmp_path)
    yield f
    f.close()


@pytest.fixture
def backend(backend_factory):
    return backend_factory(first_chunk_s=0.02, chunk_interval_s=0.02, audio_s=0.4, chunks=4)


@pytest.fixture
def client(backend):
    return backend.client


def request_body(engine="fake", voice="voz-fake", text=TEXT, **options):
    body = {"engine": engine, "voice": voice, "text": text}
    if options:
        body["options"] = options
    return body


def ws_collect(client, request, *, cancel_after=None):
    """Run one WebSocket request. Returns (start, chunks, audio_frames, summary_or_error, arrival_times).

    arrival_times[i] is the monotonic time of the i-th received message."""
    start, chunks, audio, last, arrivals = None, [], [], None, []
    with client.websocket_connect("/v1/ws/synthesize") as ws:
        ws.send_json(request)
        while True:
            msg = ws.receive()
            if msg["type"] == "websocket.close":
                break
            arrivals.append(time.monotonic())
            if msg.get("bytes") is not None:
                audio.append(msg["bytes"])
                if cancel_after is not None and len(audio) >= cancel_after:
                    break
                continue
            import json

            data = json.loads(msg["text"])
            if data["type"] == "start":
                start = data
            elif data["type"] == "chunk":
                chunks.append(data)
            else:
                last = data
                break
    return start, chunks, audio, last, arrivals
