# Quickstart: validating TTS Engine Adapters

Each engine runs in its own virtual environment (one engine per process). Commands use `uv` and run from the repo root.

## 0. Create the environments (once)
```sh
uv venv --python 3.11 .venv-core   && uv pip install -p .venv-core   -e ".[dev]"
uv venv --python 3.11 .venv-phonon && uv pip install -p .venv-phonon -e ".[phonon,dev]"
uv venv --python 3.11 .venv-pocket && uv pip install -p .venv-pocket -e ".[pocket,dev]"
uv venv --python 3.11 .venv-piper  && uv pip install -p .venv-piper  -e ".[piper,dev]"
```
Prerequisites that are not in git (Constitution Principle VI):
- `phonon-40m-es/`: `huggingface-cli download gradium/phonon-40m-es --local-dir ./phonon-40m-es`
- `cloned_voices/` with `voices.toml`, the reference WAVs and `valentina.safetensors`
- Piper voices: `.venv-piper/bin/python -m piper.download_voices --download-dir cloned_voices es_MX-claude-high es_AR-daniela-high`
- Pocket TTS cloning needs the gated terms accepted at huggingface.co/kyutai/pocket-tts and `hf auth login`.

## 1. Core + fake engine (no weights, SC-004)
```sh
.venv-core/bin/pytest tests/contract tests/unit
```
Expected: contract tests pass for the fake engine in `chunk`, `sentence`, and `none` modes; timings match the configured delays within tolerance.

## 2. Each real engine (SC-001)
```sh
.venv-phonon/bin/python -m tts_bench.smoke phonon     --voice valentina          --out /tmp/phonon.wav
.venv-pocket/bin/python -m tts_bench.smoke pocket_tts --voice valentina          --out /tmp/pocket-valentina.wav
.venv-pocket/bin/python -m tts_bench.smoke pocket_tts --voice emiliano           --out /tmp/pocket-emiliano.wav
.venv-piper/bin/python  -m tts_bench.smoke piper      --voice es_MX-claude-high  --out /tmp/piper-mx.wav
.venv-piper/bin/python  -m tts_bench.smoke piper      --voice es_AR-daniela-high --out /tmp/piper-ar.wav
```
Expected per engine: a WAV at its native sample rate, a printed descriptor (version, model id, license flags, accent), the declared streaming granularity, and time to first audio. The first call in a process is a cold start; do not read it as a steady-state number.

Optional, real-engine contract tests (cases for engines not installed in that venv are skipped):
```sh
.venv-phonon/bin/pytest tests/integration
.venv-pocket/bin/pytest tests/integration
.venv-piper/bin/pytest  tests/integration
```

## 3. Failure paths
- Extra not installed: `.venv-core/bin/python -m tts_bench.smoke piper --voice es_MX-claude-high` -> `EngineNotInstalledError` with an install hint (FR-008).
- Second engine in one process -> `EngineAlreadyLoadedError` (FR-013); covered by `tests/unit/test_one_engine_per_process.py`.
- Text over the engine limit -> `InputLimitError` (FR-015); covered by `tests/unit/test_adapter_base.py`.

## 4. Add an engine (SC-002)
See `docs/adding-an-engine.md`: copy `adapters/fake.py` as a template, implement the contract in `contracts/adapter-interface.md`, add one `register(...)` line, run the contract test suite against it.
