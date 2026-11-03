# Research: Real-Time Synthesis Backend

## R1. Hosting several engines when only one may load per process

- **Decision**: gateway + one lazy worker subprocess per engine, each launched with the engine's venv Python (from the venv map in `config.py`, e.g. `.venv-pocket/bin/python` for `pocket_tts`; `.venv-<engine>/bin/python -m tts_bench.backend.worker ENGINE`). Messages travel over the worker's stdin/stdout as length-prefixed frames; stderr goes to a per-worker log.
- **Rationale**: `core/adapter.py` raises `EngineAlreadyLoadedError` for a second engine in a process, and engines pin conflicting dependencies (separate venvs already exist). A worker keeps both rules, gives per-engine memory figures, and lets a stuck engine be killed without taking the service down. The gateway imports no engine, so it also works when no engine is installed (it lists all as unavailable with reasons).
- **Alternatives**: (a) one process, swap engines with `close()`/`load()`: slow switching, load time contaminates requests, cannot share dependencies across venvs. (b) multiprocessing from one venv: engines' dependencies conflict. (c) a separate HTTP server per engine: more ports and config for no gain.

## R2. Web framework and transport

- **Decision**: FastAPI + uvicorn for the gateway. WebSocket for streaming, plain POST for complete audio.
- **Rationale**: WebSocket carries binary audio chunks and JSON messages (start, chunk timing, final summary, error) on one connection and detects disconnects promptly, which FR-007 needs. POST gives a curl-friendly path and is the natural reply for non-streaming engines. FastAPI gives typed validation and automatic error bodies; the ASGI test client needs no real network.
- **Alternatives**: chunked HTTP with trailers (poor browser/client support for a trailing summary); Server-Sent Events (text only, base64 audio inflates size); raw `asyncio` sockets (more code to maintain).

## R3. Identical metric definitions (FR-004, US2 scenario 2)

- **Decision**: extract the arithmetic in `metrics/runner._timed_call` into `metrics/timing.py::timing_from_marks(request_started_ns, chunk_times_ns_and_sizes, finished_ns, audio_seconds, streams)` returning generation_ms, ttfa_ms (first **non-empty** chunk; `None` for granularity `none`), rtf and chunk timings. The runner and the worker both call it. The worker takes `request_started_ns` immediately before iterating the adapter, as `synthesize()` does.
- **Rationale**: one implementation cannot drift. Parity is then a test: same fake engine, same settings, offline `measure_request` versus backend, equal within the 5% tolerance (and exactly equal when fed the same marks).
- **Alternatives**: re-implement in the backend (drift risk); have the backend call `adapter.synthesize()` and stream after the fact (loses incremental delivery).
- **Note**: for streaming the worker uses `adapter.stream()`, whose generator starts on first `next()`; the worker marks `request_started_ns` just before that first `next()`. Gateway-side network and queue time are reported separately (`queue_wait_ms`) and never included.

## R4. Cancellation on disconnect (FR-007)

- **Decision**: the gateway sends `cancel` to the worker when the WebSocket closes or the HTTP client disconnects; the worker closes the adapter generator between chunks. A worker not idle within 30 s of cancel is killed and restarted (the next request reports a new `load_ms`).
- **Rationale**: engines synthesize in blocking native code; chunk boundaries are the only safe stop. For `none`/`sentence` engines the bound is one unit. Killing is the last resort and is logged.
- **Alternatives**: thread interruption (unsafe with native libraries); always kill on disconnect (reloads the model every time, destroying warm behavior).

## R5. Concurrency policy

- **Decision**: per-engine FIFO with 1 running + 2 waiting; beyond that HTTP 429 / WebSocket error `engine_busy` naming the queue depth. Different engines run concurrently (separate processes).
- **Rationale**: predictable, bounded latency, and honest: concurrent engines on one machine affect each other's timings, so each response records `concurrent_engines` (number of other active syntheses at request start) so a tester can tell a clean measurement from a contended one.
- **Alternatives**: unbounded queue (hides overload); reject all concurrency (poor for demo with two testers).

## R6. Input limit

- **Decision**: reject text over 500 characters (default, configurable) or over the engine descriptor `max_chars` if smaller; reject empty/whitespace-only text; the error states the limit and the length received.
- **Rationale**: conversational utterances are short; silent splitting would change what TTFA means (Constitution III, streaming granularity). The documented limit satisfies FR-008.

## R7. Lazy load and load time (spec edge case)

- **Decision**: a worker starts on the first request for its engine (or on `POST /v1/engines/{name}/load`); the first response carries `load_ms` (time of `adapter.load()` as in the offline harness) and `first_request_after_load: true`; later responses omit load time. Load is excluded from TTFA and generation time.
- **Rationale**: matches the cold/warm separation of the offline metrics (Constitution III).

## R8. Availability and reasons (FR-006)

- **Decision**: the catalog asks each worker for its descriptor in a short probe (`python -m tts_bench.backend.worker ENGINE --describe`) that imports the adapter, calls the new load-free `adapter.check_ready()` (dependency import, weights directory or Hugging Face cache presence) and does not load weights; a real `load()` failure at request time also flips the cached availability to `unavailable` with its reason; failures map to `venv_missing`, `not_installed`, `weights_missing` with the adapter's install/weights hint. Results are cached until `POST /v1/engines/refresh`.
- **Rationale**: `WeightsMissingError` was previously raised only inside `_load()`, so a describe probe alone could not report missing weights; `check_ready()` closes that gap with the same conditions. Reuses `EngineNotInstalledError`/`WeightsMissingError` hints already written per adapter; no model load is needed to list.
- **Note**: `descriptor.engine_version` is only known after load for some engines (`phonon`: "unknown (read at load)"); the listing shows that text until the worker loads, and the version after.

## R9. Voices without leaking voice material (FR-010)

- **Decision**: the listing builds voices from `LocalVoiceLibrary.public_index()` and **drops** `sha256` and `recording_id`, keeping `name`, `engine`, `kind`, `cloned`, `accent_label`. Resolution happens inside the gateway via `resolve(name, engine=..., use="internal_benchmarking")`; the resolved path is passed to the worker over the local pipe and never appears in any response, log or error message (errors are scrubbed of absolute paths). There is no route that serves files.
- **Rationale**: Principle VI. Consent failures return a clear "not permitted for live testing" error naming the voice, not the path.
- **Consent**: settled by the constitution (Principle VI, standing consent confirmation): all voices in `cloned_voices/` are authorized and all appear in the backend listing. Live testing resolves with `use="internal_benchmarking"`, which their consent records permit.

## R10. Offline operation (FR-009, SC-004)

- **Decision**: no outbound calls anywhere in the gateway; workers load local weights only. Engines that download on first load (`pocket_tts`) must be pre-warmed during setup; if weights are not cached the engine is listed unavailable (`weights_missing`) rather than attempting a download. A test patches `socket.create_connection` for non-loopback addresses and fails on any attempt.
- **Alternatives**: allow download on demand (violates local-first).

## R11. Request log

- **Decision**: JSONL, one line per request: timestamp, engine, voice name, text length, SHA-256 of text, outcome, metrics, queue wait, concurrency. Text itself is logged only with `--log-text`. Rotates by size.
- **Rationale**: Principle V ("every result records the exact request") and the spec edge case "recorded"; hashes keep the log shareable.
