# Quickstart: Real-Time Synthesis Backend

Validation scenarios for the feature. Contracts: [contracts/api.md](contracts/api.md); types: [data-model.md](data-model.md).

## Prerequisites

- `.venv-core` with `pip install -e '.[dev,backend]'` (gateway, fake engine, tests). No weights, no network after install.
- For real engines: each engine's existing venv (`.venv-phonon`, `.venv-pocket`, `.venv-piper`) with its weights already cached; `cloned_voices/` as in `docs/voice-preparation.md`.

## 1. Tests with the fake engine (FR-011, SC-006)

```
.venv-core/bin/python -m pytest tests/backend -q
```

Expected: all pass without weights; timing parity, cancel, concurrency, limit and privacy tests included.

## 2. Start the service

```
.venv-core/bin/python -m tts_bench.backend serve
curl -s localhost:8000/v1/health
curl -s localhost:8000/v1/engines | python -m json.tool
```

Expected: every registered engine listed with complete descriptor fields (SC-003); engines whose venv or weights are missing show `unavailable` with a reason (US3).

## 3. Stream from an engine (US1, SC-001)

Use a WebSocket client (for example `python -m websockets ws://localhost:8000/v1/ws/synthesize`) and send the request JSON of the contract. Expected: `start`, several `chunk`/audio frames, then `summary`; the first audio frame arrives before `summary` and before the last chunk is produced.

## 4. Complete audio and non-streaming notice (US1.2)

```
curl -s -D - -o out.wav -X POST localhost:8000/v1/synthesize \
  -H 'content-type: application/json' \
  -d '{"engine":"phonon","voice":"valentina-phono","text":"Hola, ¿cómo está?"}'
```

Expected: a playable WAV; for a `none` engine the response header says streaming is unavailable and TTFA is `"not available"`.

## 5. Latency parity (US2, SC-002)

With the fake engine configured for a known first-chunk delay, the summary's `ttfa_ms` and `generation_ms` match the configured values within 5%, and equal what `python -m tts_bench.metrics run fake --mode warm --limit 3` reports for the same settings.

## 6. Errors and limits

- Unknown engine or voice: error with `available` list (US1.3).
- Text over 500 characters: `text_too_long` with limit and received length (FR-008).
- Two simultaneous requests to one engine: second waits (`queue_wait_ms` > 0); beyond 2 waiting, `engine_busy` (FR-015).

## 7. Disconnect (FR-007, SC-005)

Open a stream on a slow fake engine, close the socket after the first chunk. Expected: the log shows `cancelled`, the engine is idle within one chunk interval, and the next request starts at once.

## 8. Privacy and offline (FR-009, FR-010, SC-004)

`pytest tests/backend/test_privacy.py tests/backend/test_offline.py`: no response, log or error contains a path under `cloned_voices/`, a hash or a recording id; no non-loopback connection is attempted.
