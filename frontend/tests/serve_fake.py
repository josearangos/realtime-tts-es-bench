"""Starts the gateway with the fake engine and a synthetic voice library (test helper, no weights, no real voices).

Usage: python frontend/tests/serve_fake.py PORT   (timings come from the TTS_FAKE_* environment variables)
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402

from tests.backend.conftest import ENV_NAMES, build_library  # noqa: E402
from tts_bench.backend.app import create_app  # noqa: E402
from tts_bench.backend.config import BackendConfig  # noqa: E402

port = int(sys.argv[1])
tmp = Path(tempfile.mkdtemp(prefix="tts-e2e-"))
config = BackendConfig(port=port, log_path=str(tmp / "requests.jsonl"))
config.python_overrides = {"fake": sys.executable}
config.venvs = {n: str(tmp / f"missing-{n}") for n in ("phonon", "pocket_tts", "piper")}
config.worker_env = {v: os.environ[v] for v in ENV_NAMES.values() if v in os.environ}
app = create_app(config, library=build_library(tmp / "lib", tmp))
uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
