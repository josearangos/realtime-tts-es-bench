# Contract: Real-Time Synthesis Backend API

Base URL `http://127.0.0.1:8000` (default). All JSON is UTF-8. No authentication (local only).

## GET /v1/engines

Returns `{engines: [EngineListing...]}` for every registered engine, available or not (FR-005, FR-006). Never starts a worker; never loads weights.

```json
{"engines":[{"name":"phonon","engine_version":"unknown (read at load)","license_flags":["non-commercial"],
  "streaming":{"granularity":"chunk"},"supports_cloning":true,"input_limit_chars":500,
  "voices":[{"name":"valentina-phonon","kind":"stored_voice_file","cloned":true,"accent_label":"es-CO"}],
  "availability":{"status":"available"},"state":"not_started","queue_depth":0}]}
```

Unavailable example: `"availability":{"status":"unavailable","reason":"weights_missing","hint":"Download the model with: ..."}`.

## GET /v1/engines/{name}

One listing; 404 `unknown_engine` with `available` otherwise.

## POST /v1/engines/refresh

Re-probes availability. 200 with the same body as the listing.

## POST /v1/engines/{name}/load

Optionally starts the worker and loads the engine now. 200 `{load_ms}`; same errors as synthesis for unavailable engines.

## WS /v1/ws/synthesize

Client sends one JSON message after connecting:

```json
{"engine":"phonon","voice":"valentina-phonon","text":"Buenos días, ¿en qué le puedo ayudar?","options":{"request_id":"r1"}}
```

Server messages are described in [data-model.md](../data-model.md) (`start`, repeated `chunk` + binary `audio`, `summary` or `error`). Closing the socket, or sending `{"cancel":true}`, cancels synthesis (FR-007); the server records `status: cancelled`.

Rejections before audio (unknown engine/voice, text too long, busy) are sent as an `error` message followed by a normal close; they never produce a `start`.

## POST /v1/synthesize

Same request body as the WebSocket message. Returns complete audio:

- 200 `audio/wav` (PCM16, native sample rate). Header `X-TTS-Summary` holds the `TimingSummary` JSON (TTFA is `"not available"` for granularity `none`); header `X-TTS-Streaming: unavailable` when the engine does not stream (acceptance scenario 1.2).
- Errors: JSON `ErrorBody` with status 400 (`text_empty`, `text_too_long`, `unknown_voice`), 404 (`unknown_engine`), 403 (`voice_not_permitted`), 409 (`engine_unavailable`), 429 (`engine_busy`), 500/504 (`synthesis_failed`, `empty_audio`, `worker_timeout`).

## GET /v1/health

`{status:"ok", version, limits:{max_chars, queue_waiting}}`. Works with no engine installed.

## Guarantees

| Rule | Behaviour |
|------|-----------|
| FR-010 | No route returns a voice file, reference audio, hash, recording id, consent id or filesystem path. Static file serving is not mounted. |
| FR-008 | Limit stated in `/v1/health`, in `text_too_long` errors, and in `docs/backend.md`. |
| FR-014 | `unknown_engine` and `unknown_voice` errors list valid options in `available`. |
| Binding | `127.0.0.1` by default; `--host` other than loopback prints a warning that there is no authentication. |
| Metrics | `kind: "interactive"`; queue wait and load time reported separately from TTFA and generation time. |

## CLI

```
python -m tts_bench.backend serve [--host 127.0.0.1] [--port 8000] [--config backend.toml]
                                  [--voices-dir cloned_voices] [--log-text]
python -m tts_bench.backend.worker ENGINE [--describe]     # internal; used by the gateway
```

Exit 1 on usage errors; 2 if the gateway dependencies (`fastapi`, `uvicorn`) are not installed, with `pip install -e '.[backend]'`.
