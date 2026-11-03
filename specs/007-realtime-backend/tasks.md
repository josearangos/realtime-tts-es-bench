---

description: "Task list for Real-Time Synthesis Backend"
---

# Tasks: Real-Time Synthesis Backend

**Input**: Design documents from `/specs/007-realtime-backend/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Included. Constitution Principle VIII and FR-011 require the backend to be testable with the fake engine and no model weights. All tests in `tests/backend/` use `FakeAdapter` (known delays, chunk counts, failures, granularity `none`), an in-memory/synthetic voice library and the ASGI test client: no weights, no network, no real engine venv. Only tasks marked `engine` need real engines. Test text is Spanish (Constitution II).

**Organization**: Grouped by user story. Paths follow plan.md (`src/tts_bench/backend/`, `src/tts_bench/metrics/timing.py`, `tests/backend/`). Foundational holds the shared timing helper, wire protocol, worker, supervisor, catalog core and fixtures. US1 delivers streaming, complete audio, errors, limits, queueing and cancellation. US2 delivers the timing summary exposure, parity with the offline harness, load/queue accounting and the request log. US3 delivers the engine/voice listing, availability reasons and privacy guarantees.

Consent is settled by the constitution (Principle VI, standing consent confirmation): all voices in `cloned_voices/` are authorized and listed; no task asks about or gates on consent beyond resolving with `use="internal_benchmarking"`. Voice material stays git-ignored.

No task commits anything: the maintainer makes all commits.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: US1 (stream audio), US2 (latency reporting), US3 (discovery)

---

## Phase 1: Setup

- [X] T001 Create the package `src/tts_bench/backend/__init__.py` (empty for now), and `tests/backend/__init__.py` (`output/backend/` is created on demand by the request log)
- [X] T002 Add `output/backend/` and `backend.toml` to `.gitignore` with the comment "backend request log and local engine/venv config are local-only"; confirm with `git check-ignore -v output/backend/requests.jsonl` and `git check-ignore -v backend.toml` that both ARE ignored
- [X] T003 [P] Add the optional dependency group `backend = ["fastapi", "uvicorn"]` to `pyproject.toml` (not in core `dependencies`) and add `httpx` to the `dev` group for the ASGI test client; document in `README.md` how to install it into `.venv-core` with `pip install -e ".[dev,backend]"`

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: shared timing helper (research R3), wire protocol, worker, supervisor, config, catalog core, WAV packaging, fixtures

- [X] T004 Create `src/tts_bench/metrics/timing.py` with the pure function `timing_from_marks(request_started_ns, chunks, finished_ns, audio_seconds, streams)` where `chunks` is a list of `(index, produced_at_ns, n_samples)`; it returns generation_ms (`(finished_ns - request_started_ns) / 1e6`), `ttfa_ms` (time of the first chunk with `n_samples > 0` relative to start; `None` when `streams` is false), `rtf` (`generation_ms / 1000 / audio_seconds`, never computed for `audio_seconds <= 0`) and the `ChunkTiming` list (`at_ms`, `gap_ms`) exactly as `metrics/runner._timed_call` computes them today. No I/O, standard library only
- [X] T005 Refactor `src/tts_bench/metrics/runner.py::_timed_call` to call `timing_from_marks` instead of its inline arithmetic, with no change in behavior or in the `Measurement` it returns; run `.venv-core/bin/python -m pytest tests/metrics -q` and confirm every existing test still passes (depends on T004)
- [X] T006 [P] Write `tests/backend/test_timing_helper.py`: `timing_from_marks` with hand-set marks gives the expected generation_ms, ttfa_ms, rtf and chunk gaps; an empty first chunk is skipped for TTFA; `streams=False` gives `ttfa_ms=None`; zero audio gives no rtf; the same marks fed through `runner._timed_call` and the helper give identical numbers (guards against drift, US2 scenario 2) (depends on T004, T005)
- [X] T007 [P] Implement `src/tts_bench/backend/config.py`: `BackendConfig` dataclass read from environment and an optional git-ignored `backend.toml`: `host` (default `127.0.0.1`), `port` (8000), `max_chars` (500, env `TTS_BACKEND_MAX_CHARS`), `queue_waiting` (2), `cancel_grace_s` (30), `request_timeout_s` (60), `voices_dir` (`cloned_voices`), `log_text` (false), and `venv_python(engine)` using the explicit map `fake`→`.venv-core`, `phonon`→`.venv-phonon`, `pocket_tts`→`.venv-pocket`, `piper`→`.venv-piper`, any other engine `.venv-<name>`, each as `<repo>/<venv>/bin/python`, overridable per engine in `backend.toml`; `effective_limit(descriptor)` returns `min(max_chars, descriptor.input_limits.max_chars)` ignoring `None`
- [X] T008 [P] Implement `src/tts_bench/backend/wav.py`: `float_to_pcm16(samples) -> bytes` (clip to [-1, 1], little-endian s16le, mono or interleaved channels as given) and `pcm16_to_wav(pcm, sample_rate, channels) -> bytes` using the standard library `wave`; the sample rate is never changed (data-model: "no resampling")
- [X] T009 [P] Implement `src/tts_bench/backend/protocol.py`: length-prefixed frames over a binary stream (`write_frame(stream, header: dict, payload: bytes = b"")`, `read_frame(stream) -> (dict, bytes) | None`), with header `type` one of `describe`, `load`, `synthesize`, `cancel`, `ready`, `loaded`, `start`, `chunk`, `done`, `error`; headers are UTF-8 JSON; a truncated frame raises `ProtocolError`. Standard library only
- [X] T010 [P] Write `tests/backend/test_protocol.py` and `tests/backend/test_wav.py`: frames round-trip with and without payload; EOF returns `None`; a truncated header or payload raises `ProtocolError`; `float_to_pcm16` clips values above 1.0 and below -1.0, maps 0.5 to 16383 or 16384, and the WAV produced reads back with the same sample rate, channels and frame count
- [X] T010a Add a cheap, load-free readiness check to the adapters (C1; FR-006): `BaseAdapter.check_ready() -> None` in `src/tts_bench/core/adapter.py` (default does nothing) that may raise `EngineNotInstalledError` / `WeightsMissingError` with the adapter's existing hints, and implement it in `src/tts_bench/adapters/phonon.py` (the `import ptts` check plus `model_dir` exists, the same conditions `_load` tests), `src/tts_bench/adapters/pocket_tts.py` (the `import pocket_tts` check plus the Hugging Face cache holds the `kyutai/pocket-tts` snapshot, checked by looking for its cache folder without any network call; if the cache location cannot be determined the check passes and the load-time failure handles it) and `src/tts_bench/adapters/piper.py` (the `import piper` check only; voice files are checked per voice at synthesis). `load()` behavior and existing adapter tests must be unchanged; add `tests/unit/test_check_ready.py` covering a missing import, a missing weights directory and the default no-op (no weights, no network)
- [X] T011 Implement `src/tts_bench/backend/worker.py` (`python -m tts_bench.backend.worker ENGINE [--describe]`): `--describe` imports `tts_bench.adapters`, builds the adapter via `get_adapter`, calls `adapter.check_ready()` (T010a), prints the `EngineDescriptor` as JSON and exits without loading weights (exit 2 with `{"reason": "not_installed" | "weights_missing" | "error", "hint": ...}` JSON for `EngineNotInstalledError` / `WeightsMissingError` / other errors, hints from the adapter); serve mode reads frames from stdin: `load` (times `adapter.load()` and returns `loaded` with `load_ms` and the post-load descriptor, so `engine_version` is the real one; a failing load returns an `error` frame with code `not_installed` / `weights_missing` / `load_failed`, the adapter's hint and no absolute paths, and leaves the worker able to exit cleanly), `synthesize` (receives text and the resolved voice reference `{name, kind, path_or_id}`; sets `request_started_ns = time.perf_counter_ns()` immediately before the first `next()` of `adapter.stream()` for streaming engines or before `adapter.synthesize()` for granularity `none`; writes `start` then one `chunk` frame per audio chunk with header `{index, at_ms, gap_ms, samples}` and PCM payload from `wav.float_to_pcm16`; finally `done` with the `timing_from_marks` result) and `cancel` (checked between chunks via a reader thread; closes the chunk generator and replies `done` with `status: "cancelled"`). Adapter exceptions map to `error` frames with code `synthesis_failed` / `empty_audio` / `text_too_long` (and `not_installed` / `weights_missing` if raised at synthesis, as `piper` does per voice) and a message scrubbed of absolute paths. The worker never writes audio to disk. stdout is reserved for frames; logs go to stderr (depends on T004, T008, T009, T010a)
- [X] T012 Implement `src/tts_bench/backend/supervisor.py`: `EngineSupervisor(config, engine)` that lazily spawns the worker with `config.venv_python(engine)` (`subprocess.Popen`, binary pipes, stderr to a per-engine log file under `output/backend/`), exposes `state` (`not_started` / `loading` / `ready` / `busy`), `ensure_loaded() -> load_ms | None` (returns `load_ms` only for the request that triggered the load, data-model "first-request"), and an async `synthesize(request) -> AsyncIterator[frame]` guarded by a per-engine `asyncio` lock with a waiting counter: one running, `config.queue_waiting` waiting, a further request raises `EngineBusyError(queue_depth)` immediately; measures `queue_wait_ms` from enqueue to lock acquisition; `cancel()` sends the `cancel` frame and, if the worker is not idle within `config.cancel_grace_s`, kills and restarts it (state returns to `not_started`, logged as `killed`); a worker that dies mid-request yields an error `worker_crashed` and state `not_started`. A module-level counter gives `concurrent_engines` (other engines with an active synthesis when this request starts) (depends on T009, T011, T007)
- [X] T013 [P] Implement `src/tts_bench/backend/catalog.py` core (listing views come in US3): `registered_engines()` from `tts_bench.core.registry.registered_names()` after importing `tts_bench.adapters`; `voices_for(engine, library)` built from `LocalVoiceLibrary.public_index()` keeping ONLY `name`, `kind`, `cloned`, `accent_label` (never `sha256` or `recording_id`; FR-010) and filtered to the engine; an engine with no library voices is listed with an empty `voices` list and a `note` ("no voices registered in the library"); a request for such an engine fails with `unknown_voice` listing nothing rather than inventing a voice; `resolve_voice(engine, voice, library)` calling `library.resolve(voice, engine=engine, use="internal_benchmarking")` and returning the `VoiceReference`; `probe(engine, config)` running the worker with `--describe` under the engine's venv (timeout 20 s) and mapping failures to `availability = {status, reason in venv_missing | not_installed | weights_missing | error, hint}` (a missing venv python gives `venv_missing`); results cached until `refresh()` (depends on T007, T011)
- [X] T014 Implement `src/tts_bench/backend/app.py` skeleton: `create_app(config=None, supervisors=None, library=None)` building a FastAPI app with an error-mapping layer that turns domain errors into `ErrorBody` JSON (`{error, message, available?, limit?, received?, queue_depth?}`) with the status codes of contracts/api.md; a response/log scrubber that replaces any absolute filesystem path in messages with `<path>`; `GET /v1/health` returning `{status, version, limits: {max_chars, queue_waiting}}`; no static file mounting and no route that serves files (FR-010). Import of `fastapi` is guarded: when missing, `__main__` exits 2 with `pip install -e '.[backend]'` (depends on T007, T013)
- [X] T014a [P] Implement `src/tts_bench/backend/requestlog.py`: `RequestLog(path, log_text)` appending JSON Lines to `output/backend/requests.jsonl` with the fields of data-model "RequestLogEntry" (including `engine_version`, `model_id`), size-based rotation (default 5 MiB, keep 3), thread-safe, creating the directory on demand; expose `log_request(...)` for all outcomes (`ok`, `failed`, `invalid`, `cancelled`, `rejected`); wired into the WebSocket and POST paths by T022/T023 (depends on T007)
- [X] T015 [P] Create `tests/backend/conftest.py`: a `FakeWorkerFactory` fixture that builds supervisors running `python -m tts_bench.backend.worker fake` with the current interpreter (the fake adapter gets its timings from environment variables `TTS_FAKE_FIRST_CHUNK_S`, `TTS_FAKE_CHUNK_INTERVAL_S`, `TTS_FAKE_AUDIO_S`, `TTS_FAKE_CHUNKS`, `TTS_FAKE_GRANULARITY`, `TTS_FAKE_LOAD_S`, `TTS_FAKE_FAIL_AFTER` read by the worker only when `ENGINE == "fake"`, plus `TTS_FAKE_DESCRIBE_FAIL=<not_installed|weights_missing|error>` making `--describe` and `load` fail with that reason and its hint, so unavailability paths are testable without real engines), a `client` fixture using the ASGI test client against `create_app` with that factory and a synthetic `LocalVoiceLibrary` rooted in `tmp_path` (never the real `cloned_voices/`) in which `fake` voices are registered with `register_fixed(name, "fake", <tiny file in tmp_path>, accent_label="none (synthetic tone)", creation="test")` plus one cloned-style entry with a synthetic reference recording; first read `register_fixed`/`register` and, if `engine="fake"` is rejected, add the minimal engine-agnostic allowance in `voices/library.py` with a test, a `ws_collect(client, request)` helper returning `(start, chunks, audio_frames, summary_or_error, arrival_times)`, and teardown that stops every worker. Add the matching env-var handling to `worker.py` (depends on T011, T012, T014)

**Checkpoint**: foundation ready, user stories can start

---

## Phase 3: User Story 1 - Stream synthesized audio from any engine (Priority: P1) 🎯 MVP

**Goal**: a tester sends engine, voice and Spanish text and receives audio incrementally when the engine streams, or complete audio with a clear notice when it does not; unknown engines/voices, empty or too-long text, busy engines and disconnects are handled predictably.

**Independent Test**: with the fake engine, the first audio frame arrives before the last chunk is produced (SC-001); a `none` engine returns complete audio with the "streaming not available" notice; errors list the available options.

### Tests for User Story 1

- [X] T016 [P] [US1] Write `tests/backend/test_streaming.py` (FR-001, FR-002, FR-003; acceptance 1.1, 1.2): fake engine with 4 chunks and 50 ms between chunks over WebSocket gives `start`, 4 `chunk` messages each followed by a binary frame, then `summary`; the first binary frame arrives at least one chunk interval before the `summary` and before the worker's last chunk time (SC-001); PCM total bytes equal `samples * 2` and the `start` message states `sample_format: "s16le"`, native `sample_rate` and `streaming: true`; for granularity `none` exactly one audio frame carries the complete audio and `start` has `streaming_available: false` with a notice; `POST /v1/synthesize` returns a WAV that `wave` can read, with header `X-TTS-Streaming: unavailable` for the `none` engine and no such header for a streaming one; the request body's `options.request_id` is echoed
- [X] T017 [P] [US1] Write `tests/backend/test_errors.py` (FR-014; acceptance 1.3): unknown engine gives `unknown_engine` with `available` listing registered available engines (HTTP 404); unknown voice gives `unknown_voice` with `available` listing that engine's voices (400); a voice of another engine is treated as unknown for this engine; an engine listed unavailable (`TTS_FAKE_DESCRIBE_FAIL=weights_missing`) gives `engine_unavailable` (409) with the reason and hint, not a generic failure; `synthesis_failed` when the fake engine raises after 2 chunks (the WebSocket sends an `error` message after the chunks already sent; POST returns 500); empty audio gives `empty_audio`; no message contains a path
- [X] T018 [P] [US1] Write `tests/backend/test_limits.py` (FR-008): text of exactly `max_chars` is accepted, `max_chars + 1` gives `text_too_long` with `limit` and `received` (HTTP 400, WebSocket `error` before any `start`); an engine whose descriptor `max_chars` is lower than the config limit uses the lower one; empty and whitespace-only text give `text_empty`; text is not split or truncated; the limit appears in `GET /v1/health`
- [X] T019 [P] [US1] Write `tests/backend/test_concurrency.py` (FR-015): two simultaneous requests to one fake engine are served one after the other, the second reports `queue_wait_ms` roughly equal to the first's generation time (tolerance 25%) and its TTFA is NOT inflated by that wait; with 1 running and 2 waiting, a fourth gets `engine_busy` (429 / WebSocket error) naming `queue_depth` without waiting; two different engines (two fake-named supervisors) run concurrently and each reports `concurrent_engines: 1`; each outcome is recorded in the request log (T014a)
- [X] T020 [P] [US1] Write `tests/backend/test_cancel.py` (FR-007, SC-005): over WebSocket on a slow fake engine (10 chunks, 100 ms apart), close the socket after the first chunk; the worker stops within one chunk interval plus tolerance (assert stop time < 2 chunk intervals), the supervisor state returns to `ready`, the next request starts immediately and succeeds; the same via a `{"cancel": true}` message; a worker made unresponsive (ignores cancel) is killed after `cancel_grace_s` (set to 1 s in the test), the state becomes `not_started`, and the following request reloads and reports a new `load_ms`; the log (T014a) records `cancelled`

### Implementation for User Story 1

- [X] T021 [US1] Implement request validation in `src/tts_bench/backend/app.py` (`SynthesisRequest` model per data-model: `engine` registered and available, `voice` belongs to the engine, `text` non-empty after trim and length <= `config.effective_limit(descriptor)`, `options.stream` default true, `options.request_id` generated if absent); errors raise the domain exceptions mapped in T014 with `available` lists taken from `catalog` (depends on T013, T014)
- [X] T022 [US1] Implement `WS /v1/ws/synthesize` in `src/tts_bench/backend/app.py`: accept, read the request JSON, validate (T021), resolve the voice through `catalog.resolve_voice` (never forward anything but the resolved reference to the worker), acquire the supervisor slot, emit `start` (request_id, engine, `engine_version`, `model_id`, voice, accent_label, `spanish_variant`, granularity, sample_rate, channels, `sample_format: "s16le"`, `streaming`, `streaming_available: false` plus notice for granularity `none`, `queue_wait_ms`, `load_ms` when this request loaded the engine, `concurrent_engines`), then for each worker `chunk` frame send the JSON `chunk` message followed immediately by the binary PCM frame, then `summary` (or `error`); on `WebSocketDisconnect`, a `{"cancel": true}` message or a send failure call `supervisor.cancel()` and finish with status `cancelled`. Every outcome, including rejections before audio, is written with `RequestLog` (T014a). Rejections before audio send an `error` message and close normally (depends on T012, T021)
- [X] T023 [US1] Implement `POST /v1/synthesize` in `src/tts_bench/backend/app.py`: same validation, supervisor path and `RequestLog` (T014a) entries; collect all PCM, return `audio/wav` via `wav.pcm16_to_wav`, header `X-TTS-Streaming: unavailable` when granularity is `none`, header `X-TTS-Summary` carrying the summary JSON (ASCII-safe, compact); errors as `ErrorBody` with the statuses of contracts/api.md; detect client disconnect with `request.is_disconnected()` and cancel (depends on T022)
- [X] T024 [P] [US1] Implement `src/tts_bench/backend/__main__.py`: `python -m tts_bench.backend serve [--host 127.0.0.1] [--port 8000] [--config backend.toml] [--voices-dir cloned_voices] [--log-text]` running `uvicorn` on the app; a non-loopback `--host` prints "warning: the backend has no authentication; only expose it on trusted networks" to stderr; exit 1 on usage errors, 2 when `fastapi`/`uvicorn` are missing with the `pip install -e '.[backend]'` hint; shuts down every worker on exit (depends on T014)

**Checkpoint**: User Story 1 works end to end with the fake engine

---

## Phase 4: User Story 2 - Report latency with every response (Priority: P1)

**Goal**: every response carries TTFA, generation time, audio duration and RTF measured server-side with the same definitions as the offline metrics; load and queue time are reported separately; each request is logged.

**Independent Test**: with the fake engine of known delay, reported latency matches within 5% (SC-002) and equals the offline harness for the same settings.

### Tests for User Story 2

- [X] T025 [P] [US2] Write `tests/backend/test_timing.py` (FR-004, SC-002; acceptance 2.1): fake engine with `first_chunk_delay_s=0.2`, 4 chunks, 0.05 s between chunks: the summary's `ttfa_ms` is within 5% of 200 and `generation_ms` within 5% of 350, `audio_seconds` equals the configured audio length exactly, `rtf` equals `generation_ms / 1000 / audio_seconds`, `chunks` is 4, `kind` is `"interactive"`, `granularity` is echoed, and `start` carries `engine_version`, `model_id` and `spanish_variant` of the engine; the same summary appears in the WebSocket `summary` and the POST `X-TTS-Summary` header; granularity `none` gives `ttfa_ms: "not available"` and never a number (FR-012); zero-length audio gives `empty_audio`, not an RTF
- [X] T026 [P] [US2] Write `tests/backend/test_timing_parity.py` (acceptance 2.2): run `metrics.runner.measure_request` on a `FakeAdapter` with the same settings as the worker env and compare with the backend summary for the same sentence: `ttfa_ms`, `generation_ms` and `rtf` agree within 5%, and feeding identical marks to both paths gives exactly equal values; the field definitions listed in `docs/backend.md` match the table in `docs/metrics.md` (a test reads both files and checks the metric names and start/end instants phrases)
- [X] T027 [P] [US2] Write `tests/backend/test_load_time.py`: with `TTS_FAKE_LOAD_S=0.3`, the first request's `start` and `summary` carry `load_ms` within 5% of 300 plus `first_request_after_load: true`, and its `ttfa_ms` / `generation_ms` do NOT include the load; the second request has no `load_ms`; after a worker kill the next request reports a new `load_ms`; `POST /v1/engines/{name}/load` returns `load_ms` and a following request has none
- [X] T028a [P] [US2] Write `tests/backend/test_timeout.py`: a fake engine slower than `request_timeout_s` (set to 1 s) gives `worker_timeout` (HTTP 504, WebSocket `error`), the worker is cancelled/killed per the grace rule and the next request succeeds; the outcome is logged as `failed`
- [X] T028 [P] [US2] Write `tests/backend/test_requestlog.py`: each outcome (`ok`, `failed`, `invalid`, `cancelled`, `rejected` including `engine_busy` and `text_too_long`) appends one JSON line with `ts`, `request_id`, `engine`, `voice`, `text_chars`, `text_sha256`, `status`, `error?`, `summary?`, `concurrent_engines`; the text itself is absent unless `log_text=true`; no line contains a path or audio; the file rotates when it exceeds the configured size

### Implementation for User Story 2

- [X] T029 [US2] Expose the full `TimingSummary` (data-model) in `summary` messages and `X-TTS-Summary`: `ttfa_ms` (number or the string `"not available"`), `generation_ms`, `audio_seconds`, `rtf`, `chunks`, `queue_wait_ms`, `load_ms` only when this request loaded the engine, `granularity`, `kind: "interactive"`; queue wait and load time are never added to the other fields (depends on T022, T023)
- [X] T030 [US2] Add `POST /v1/engines/{name}/load` to `src/tts_bench/backend/app.py` returning `{load_ms}` (or `{load_ms: null, already_loaded: true}`), mapping unavailable engines to `engine_unavailable` (depends on T012, T014)
- [X] T032 [US2] Write the first version of `docs/backend.md`: how to install and start the service, the endpoints, the metric definitions table (copied by reference from `docs/metrics.md`: TTFA, generation time, audio duration, RTF, chunk latency, with start and end instants, plus queue wait and load time defined as separate quantities), the statement that backend figures are `interactive` and MUST NOT be compared with `results/perf/` benchmark figures (Constitution III), the input limit, the concurrency policy, the cancellation bound (next chunk boundary; end of the sentence for `sentence`/`none` granularity; 30 s then kill), and the log format; add a link to it in `docs/metrics.md` "See also" and in `README.md`

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: User Story 3 - Discover engines, voices and their properties (Priority: P2)

**Goal**: a client lists all registered engines with descriptor fields, voices, streaming granularity, cloning support, licenses and availability with reasons, without starting any worker and without exposing voice material.

**Independent Test**: the listing returns complete descriptor fields for each registered engine; an engine with a missing venv or weights is shown as unavailable with the reason.

### Tests for User Story 3

- [X] T033 [P] [US3] Write `tests/backend/test_catalog.py` (FR-005, FR-006, SC-003; acceptance 3.1, 3.2): `GET /v1/engines` lists every registered engine (`fake`, `phonon`, `pocket_tts`, `piper`) with `name`, `engine_version`, `model_id`, `license_code`, `license_model`, `license_flags`, `language`, `spanish_variant`, `supports_cloning`, `voice_kind`, `streaming.granularity`, `input_limit_chars`, `voices`, `availability`, `state`, `queue_depth` (a parametrized check that no field is missing for any engine); an engine whose venv path does not exist is `unavailable` with `reason: "venv_missing"` and a hint; with `TTS_FAKE_DESCRIBE_FAIL=weights_missing` the engine is `unavailable` with that reason and the adapter-style hint, and a `load` that fails at request time flips the cached availability to `unavailable` with the same reason (the request gets `engine_unavailable`, not a generic failure); the listing never spawns a loading worker (supervisor state stays `not_started`; only `--describe` probes run); `non-commercial` and `copyleft` flags are present for `phonon` and `piper`; `GET /v1/engines/{name}` returns one listing and 404 `unknown_engine` with `available`; `POST /v1/engines/refresh` re-probes after a venv appears; an adapter-declared hint (weights/install) is passed through for `weights_missing` / `not_installed` (via `TTS_FAKE_DESCRIBE_FAIL`)
- [X] T034 [P] [US3] Write `tests/backend/test_privacy.py` (FR-010, Principle VI): with a synthetic library containing a cloned voice, every voice object in the listing has exactly the keys `name`, `kind`, `cloned`, `accent_label`; no response body, header, WebSocket message, error message or log line, across success and every error path, contains the substring of the library root, `.safetensors`, `.wav` paths, a `sha256` value of any voice file, a `recording_id` or a consent id; there is no route under `/static`, `/files`, `/voices` or `/cloned_voices` (each returns 404/405); requesting a path traversal such as `/v1/../cloned_voices/library.json` returns 404; all voices of the library for an engine appear in its listing (no filtering by consent, per the constitution)
- [X] T035 [P] [US3] Write `tests/backend/test_offline.py` (FR-009, SC-004): patch `socket.socket.connect` / `socket.create_connection` so any non-loopback address raises, then start the app, list engines, stream a fake-engine request and cancel one; assert no attempt was made; the default host is `127.0.0.1`; a non-loopback `--host` prints the no-authentication warning; the app imports no module that opens network clients at import time (checked by importing `tts_bench.backend.app` under the same patch)

### Implementation for User Story 3

- [X] T036 [US3] Implement `GET /v1/engines`, `GET /v1/engines/{name}` and `POST /v1/engines/refresh` in `src/tts_bench/backend/app.py` using `catalog` (descriptor from the probe or, after load, from the worker's `loaded` frame so `engine_version` becomes the real version; voices from `catalog.voices_for`; `state` and `queue_depth` from the supervisor; availability from the cached probe); the listing never starts a loading worker (depends on T013, T012, T014)
- [X] T037 [US3] Harden `catalog.py` and `app.py` for FR-010: build every voice object from an explicit allow-list of four keys (not by deleting keys from the index), apply the path scrubber of T014 to all error messages and log lines, and confirm `LocalVoiceLibrary` errors (`VoiceIntegrityError`, `VoiceNotFoundError`) are rewritten to path-free messages naming only the voice (depends on T013, T014)

**Checkpoint**: all three user stories work independently

---

## Phase 6: Polish & Cross-Cutting

- [X] T038 [P] Write `tests/backend/test_engines_real.py` marked `@pytest.mark.engine` (skipped by default, run with the real venvs available): for each of `phonon`, `pocket_tts` and `piper` start a real worker through the supervisor, request one Spanish sentence with a library voice that matches the engine, and assert audio arrives, TTFA is a number for streaming engines and `"not available"` for non-streaming ones, and the summary carries `kind: "interactive"`; record the commands in the docstring
- [X] T039 [P] Add a gateway overhead test in `tests/backend/test_overhead.py`: with the fake engine at 4 chunks, the difference between the worker-reported chunk `at_ms` and the client-observed arrival offset is under 5 ms at p95 over 50 requests, on the test machine (plan Performance Goal; reported, skipped with a clear message if the machine is under load)
- [X] T040 Update `docs/backend.md` with the listing fields and availability reasons, the voices-never-exposed guarantee and the standing consent note (all library voices are listed; reference to Constitution Principle VI), and the venv map and `backend.toml` format; state that `total time` in the spec is `generation_ms` in the API and that the engine-level `spanish_variant` is indicative while the voice's `accent_label` is the accent to report (for `piper` it follows the selected voice); update `README.md` with a short "Real-time backend" section and the quickstart commands
- [X] T041 Run the whole quickstart (`specs/007-realtime-backend/quickstart.md` sections 1 to 8) with the fake engine and, where venvs and cached weights exist, with the real engines; record any deviation in `docs/backend.md`; confirm `pocket_tts` is listed `unavailable` with `weights_missing` (and not downloading) when its weights are not cached
- [X] T042 Run the full regression `.venv-core/bin/python -m pytest -q` (excluding `engine` marked tests) and confirm features 001 to 006 tests still pass after the `runner.py` refactor; run `git status` and confirm no voice material, audio, `backend.toml` or `output/backend/` file is tracked or staged

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup; blocks all stories. Internal order: T004 → T005 → T006; T010a (adapter `check_ready`) and T004, T008, T009 → T011 → T012; T007, T011 → T013; T007, T013 → T014; T007 → T014a; T011, T012, T014 → T015
- **User Story 1 (Phase 3)**: depends on Foundational. T021 → T022 → T023; T024 independent after T014
- **User Story 2 (Phase 4)**: depends on Foundational and on T022/T023 (it exposes and verifies what US1 streams); T014a (Foundational) feeds the log assertions in T019/T020/T028
- **User Story 3 (Phase 5)**: depends on Foundational only; independent of US1/US2 implementation (the listing uses the catalog and supervisor state)
- **Polish (Phase 6)**: after the desired stories

### Within each story

- Tests are written first and must fail before implementation
- Validation before endpoints; WebSocket before POST (POST reuses the same supervisor path)

### Parallel Opportunities

- Setup: T003 alongside T001/T002
- Foundational: T006, T007, T008, T009, T010, T010a, T013, T014a and T015 touch different files and can run in parallel once their dependencies exist
- US1 tests T016–T020 are all `[P]`; US2 tests T025–T028 are all `[P]`; US3 tests T033–T035 are all `[P]`
- US3 can be built in parallel with US1/US2 by a second worker after Foundational

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Streaming tests in tests/backend/test_streaming.py"
Task: "Error tests in tests/backend/test_errors.py"
Task: "Limit tests in tests/backend/test_limits.py"
Task: "Concurrency tests in tests/backend/test_concurrency.py"
Task: "Cancel tests in tests/backend/test_cancel.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup, then Phase 2 Foundational (including the `timing_from_marks` refactor and its regression run)
2. Phase 3 User Story 1
3. **Stop and validate**: quickstart sections 1, 3, 4, 6 and 7 with the fake engine

### Incremental Delivery

1. Add User Story 2 (latency exposure, parity, load/queue accounting, log) and validate quickstart section 5
2. Add User Story 3 (listing, availability, privacy, offline) and validate sections 2 and 8
3. Polish: real-engine test, overhead check, docs, full regression

---

## Notes

- Every functional requirement maps to a task: FR-001/002/003 → T016, T022, T023; FR-004 → T004, T025, T026, T029; FR-005/006 → T010a, T013, T033, T036; FR-007 → T020, T022; FR-008 → T018, T021; FR-009 → T035; FR-010 → T034, T037; FR-011 → T015 and the whole `tests/backend/` suite; FR-012 → T016, T025; FR-013 → T027; FR-014 → T017; FR-015 → T019, T014a (recorded)
- Success criteria: SC-001 → T016; SC-002 → T025, T026; SC-003 → T033; SC-004 → T035; SC-005 → T020; SC-006 → whole suite run in `.venv-core` with no weights
- Live numbers are `interactive`; never merge them into `results/perf/` comparisons
- The maintainer makes all commits
