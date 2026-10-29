# Quickstart: validating TTS Engine Adapters

Each engine runs in its own virtual environment (one engine per process).

## 1. Core + fake engine (no weights, SC-004)
```sh
python3.11 -m venv .venv-core && . .venv-core/bin/activate
pip install -e ".[dev]"
pytest tests/contract tests/unit
```
Expected: contract tests pass for the fake engine in `chunk`, `sentence`, and `none` modes; timings match the configured delays within tolerance.

## 2. Each real engine (SC-001)
```sh
python3.11 -m venv .venv-phonon && . .venv-phonon/bin/activate && pip install -e ".[phonon]"
python -m tts_bench.smoke phonon --voice <name-from-voice-library>
```
Repeat with `.[pocket]` / `pocket_tts` and `.[piper]` / `piper` (dependency group name, then engine registry name).
Expected per engine: a WAV with its native sample rate, a printed descriptor (version, model id, license flags, accent), and the declared streaming granularity.

## 3. Failure paths
- Run `smoke` with the extra not installed: expect an install hint (FR-008).
- Load a second engine in one process: expect `EngineAlreadyLoadedError` (FR-013).
- Pass text over the engine limit: expect `InputLimitError` (FR-015).

## 4. Add an engine (SC-002)
Copy `adapters/fake.py` as a template, implement the contract in `contracts/adapter-interface.md`, add one `register(...)` line, run the contract test suite against it.
