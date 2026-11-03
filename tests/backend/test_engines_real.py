"""Real engines through the backend (skipped unless TTS_BACKEND_REAL_ENGINES=1).

Run with the engine venvs and cached weights in place:

    TTS_BACKEND_REAL_ENGINES=1 .venv-core/bin/python -m pytest tests/backend/test_engines_real.py -m engine -q

Uses the real, git-ignored `cloned_voices/` library read-only (all voices are authorized,
Constitution Principle VI); audio is never written.
"""

import json
import os

import pytest

from tests.backend.conftest import request_body, ws_collect
from tts_bench.backend.app import create_app
from tts_bench.backend.config import BackendConfig

pytestmark = pytest.mark.engine

CASES = [("phonon", "valentina-phonon"), ("pocket_tts", "valentina-pocket"), ("piper", "es_MX-claude-high")]


@pytest.fixture(scope="module")
def real_client(tmp_path_factory):
    if os.environ.get("TTS_BACKEND_REAL_ENGINES") != "1":
        pytest.skip("set TTS_BACKEND_REAL_ENGINES=1 to run real engines")
    from fastapi.testclient import TestClient

    config = BackendConfig(log_path=str(tmp_path_factory.mktemp("log") / "requests.jsonl"))
    with TestClient(create_app(config)) as client:
        yield client


@pytest.mark.parametrize("engine,voice", CASES)
def test_real_engine_streams_spanish(real_client, engine, voice):
    listing = real_client.get(f"/v1/engines/{engine}").json()
    if listing["availability"]["status"] != "available":
        pytest.skip(f"{engine} unavailable: {listing['availability']}")
    start, chunks, audio, last, _ = ws_collect(real_client, request_body(engine=engine, voice=voice,
                                                                         text="Buenos días, ¿en qué le puedo ayudar?"))
    assert audio and last["type"] == "summary", last
    assert last["kind"] == "interactive"
    if listing["streaming"]["granularity"] == "none":
        assert last["ttfa_ms"] == "not available"
    else:
        assert isinstance(last["ttfa_ms"], float)
    json.dumps(last)
